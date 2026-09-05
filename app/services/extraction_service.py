"""Information extraction: convert OCR text into structured fields.

This is deterministic (regex + normalization + keyword matching), NOT an LLM.
OCR gives raw text + confidence; this service turns it into fields like:

  net_quantity = {value: 500, unit: "g"}
  mrp = 450
  manufacturer = "ABC Foods"
  packing_date = "08/2026"

Fields are extracted to feed the Rule Engine. Extraction never decides
compliance — it only produces structured evidence.
"""

import re
from dataclasses import dataclass, field

# Reward tokens that commonly appear after "MRP" and before the price.
# OCR frequently misreads the ₹ / Rs symbol as <, >, {, (, etc.
_MRP_RES = [
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)?\s*:?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMax\w*\.?\s*Retail\s+Price\s*:?\s*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    # OCR disfigurement of "MRP": "4VAP", "MRRP", "MRF" etc followed by Rs/₹
    re.compile(r"\bM{1,2}[RPI]{1,2}[PI]?\s*(?:Rs\.?|INR|₹)\s*:?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
    # MRP followed by a stray symbol (OCR misread of ₹/Rs as < > { ( | etc.)
    re.compile(r"\bMRP\s*[:\-]?[\s]*[<>{(\[\]\|`'\"~@#&*]+[\s]*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
    # "MRP Rs. 120" / "MRP: 120" / "M.R.P. 120"
    re.compile(r"\bM\.?R\.?P\.?\s*:?\s*(?:Rs\.?|INR|₹)?\s*[<>{(\[\]\|`'\"~@#&*]*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
]

_UNIT_PATTERNS = {
    "weight": ["kg", "g", "milligram", "mg", "tonne", "ton"],
    "volume": ["litre", "liter", "l", "ml", "cl", "dl", "millilitre", "milliliter"],
    "number": ["nos", "pieces", "pcs", "count", "units", "tablets", "capsules", "sheets", "pairs"],
    "length": ["mm", "cm", "m", "km"],
}

# Unit aliases -> canonical
_UNIT_CANON = {
    "kg": ("weight", "kg"), "kilogram": ("weight", "kg"), "kgs": ("weight", "kg"),
    "g": ("weight", "g"), "gram": ("weight", "g"), "gm": ("weight", "g"), "gms": ("weight", "g"), "grams": ("weight", "g"),
    "ml": ("volume", "ml"), "millilitre": ("volume", "ml"), "milliliter": ("volume", "ml"), "cc": ("volume", "ml"),
    "l": ("volume", "l"), "litre": ("volume", "l"), "liter": ("volume", "l"),
    "mg": ("weight", "mg"), "milligram": ("weight", "mg"),
    "nos": ("number", "nos"), "no": ("number", "nos"), "pieces": ("number", "nos"),
    "pcs": ("number", "nos"), "tablets": ("number", "nos"), "capsules": ("number", "nos"),
    "sheets": ("number", "nos"),
    "cm": ("length", "cm"), "mm": ("length", "mm"), "m": ("length", "m"), "mt": ("length", "m"),
}

_DATE_RES = [
    # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"),
    # MM/YYYY or MM-YYYY
    re.compile(r"\b(\d{1,2})[/\-.](\d{4})\b"),
    # Month YYYY
    re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})\b", re.IGNORECASE),
]

_CONTACT_RES = {
    "phone": re.compile(r"(?:\+?\d[\d\s\-]{7,15}\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "website": re.compile(r"\b(?:www\.)[\w.\-]+\.\w+\b|\bhttps?://[^\s]+\b"),
}


@dataclass
class ExtractedField:
    """One extracted structured field."""

    field_name: str
    value: str | None = None
    numeric: float | None = None
    unit: str | None = None
    confidence: float = 0.0
    source_text: str | None = None


@dataclass
class ExtractionResult:
    """All structured fields extracted from an analysis's OCR text."""

    fields: dict = field(default_factory=dict)  # field_name -> ExtractedField
    raw_text: str = ""

    def get(self, name: str) -> ExtractedField | None:
        return self.fields.get(name)

    def has(self, name: str) -> bool:
        f = self.fields.get(name)
        return f is not None and bool(f.value)


def _clean_text(text: str) -> str:
    # normalize whitespace WITHIN each line but preserve line structure
    lines = [re.sub(r"\s+", " ", ln.replace("\u00a0", " ")).strip() for ln in text.splitlines()]
    return "\n".join(l for l in lines if l).strip()


def extract_net_quantity(text: str) -> ExtractedField | None:
    """Find 'Net Wt. 500 g', 'Net quantity 1 l', 'Net Content: 50 ml', etc."""
    m = re.search(
        r"\b(?:net\s*(?:wt\.?|weight|qty\.?|quantity|contents?)?|nel\s*(?:conlent|content|qty)|n\.?\s*w\.?)\s*[:\-]?\s*"
        r"(\d+(?:\.\d+)?)\s*(kg|kg\.|g|gm|g\.|grams?|ml|l|lit(?:re|er)s?|millilit(?:re|er)s?|nos\.?|pcs\.?|pieces?|tablets?|capsules?|cm|mm|m|cl|dl|%)\b",
        text,
        re.IGNORECASE,
    )
    if not m:
        # Net weight label present but unit/value unreadable (e.g. OCR noise):
        # cap the value from a nearby number so validators can mark REVIEW
        # instead of FAIL-on-missing.
        has_label = re.search(r"\bnet\s*(?:wt\.?|weight|qty\.?|quantity|contents?)\b", text, re.IGNORECASE)
        if has_label:
            return ExtractedField(
                field_name="net_quantity",
                value=None,
                confidence=0.3,
                source_text=has_label.group(0),
            )
        return None
    value = float(m.group(1))
    raw_unit = m.group(2).lower().rstrip(".")
    info = _UNIT_CANON.get(raw_unit)
    if info is None:
        return None
    kind, unit = info
    # normalize to smallest sensible: convert kg->g, l->ml for comparison
    numeric_g = value
    if unit == "kg":
        numeric_g = value * 1000
        unit = "g"
    if unit in ("l",):
        numeric_g = value * 1000
        unit = "ml"
    return ExtractedField(
        field_name="net_quantity",
        value=f"{value} {raw_unit}",
        numeric=numeric_g,
        unit=unit,
        confidence=0.9,
        source_text=m.group(0),
    )


def _parse_mrp_value(raw: str) -> float:
    """Parse captured MRP number, stripping commas."""
    return float(raw.replace(",", ""))


def _try_post_match_recovery(match, text: str) -> float | None:
    """After a primary regex matched, check if the leading digit is a misread ₹.

    When OCR reads "MRP: ₹650" as "MRP: 7650", the first regex captures 7650.
    This function detects that the MRP label is followed by a digit (not ₹/Rs)
    and tries replacing the leading digit with ₹ to recover the true value.
    """
    source = match.group(0)
    captured = match.group(1)
    if not captured or len(captured) < 2:
        return None

    # Skip only if ₹ appears immediately before the captured digits
    digit_pos = source.find(captured)
    if digit_pos > 0 and source[digit_pos - 1] == "₹":
        return None

    first_digit = captured[0]
    if first_digit not in "3789":
        return None

    if digit_pos < 0:
        return None

    # If Rs./INR is already in the source, the ₹ was misread as an extra
    # leading digit. Strip it instead of inserting ₹ (which would conflict).
    has_other_currency = bool(re.search(r"Rs\.?|INR", source, re.IGNORECASE))
    if has_other_currency:
        stripped = captured[1:]
        if stripped:
            val = _parse_mrp_value(stripped)
            if val > 0:
                return val
        return None

    # Otherwise, replace the leading digit with ₹ and re-match
    recovered_source = source[:digit_pos] + "₹" + captured[1:]
    recovered_text = text[: match.start()] + recovered_source + text[match.end():]
    for r2 in _MRP_RES:
        m2 = r2.search(recovered_text)
        if m2:
            return _parse_mrp_value(m2.group(1))
    return None


def extract_mrp(text: str) -> ExtractedField | None:
    for rx in _MRP_RES:
        m = rx.search(text)
        if m:
            val = _parse_mrp_value(m.group(1))
            recovered = _try_post_match_recovery(m, text)
            if recovered is not None:
                val = recovered
            return ExtractedField(
                field_name="mrp",
                value=f"{val:g}",
                numeric=val,
                confidence=0.95,
                source_text=m.group(0),
            )
    # ₹ symbol recovery: OCR may read ₹ as 3/7/8/9.  When MRP label is
    # present but no primary regex matched, try replacing a leading digit
    # in the price position with ₹ and retry.
    recovered_text = _try_rupee_recovery(text)
    if recovered_text:
        for rx in _MRP_RES:
            m = rx.search(recovered_text)
            if m:
                val = _parse_mrp_value(m.group(1))
                return ExtractedField(
                    field_name="mrp",
                    value=f"{val:g}",
                    numeric=val,
                    confidence=0.85,
                    source_text=m.group(0),
                )
    return None


_MRP_LABEL_RE = re.compile(
    r"\b(?:max\.?\s*retail\s*price|m\.?r\.?p\.?)\b", re.IGNORECASE
)


def _try_rupee_recovery(text: str) -> str | None:
    """Try to recover ₹ misread as a leading digit before an MRP label.

    When OCR reads "MRP: ₹650" as "MRP: 7650" (or 3650 etc.), the leading
    digit is actually a mangled ₹ symbol.  Localized to MRP context only.
    """
    if not text:
        return None
    for rx in _MRP_RES:
        if rx.search(text):
            return None  # primary regex already works
    lm = _MRP_LABEL_RE.search(text)
    if not lm:
        return None
    after = text[lm.end():]
    m = re.match(r"^\s*(\d)", after)
    if not m:
        return None
    digit = m.group(1)
    recovered = text[:lm.end()] + "₹" + after[m.end():]
    for rx in _MRP_RES:
        if rx.search(recovered):
            return recovered
    return None


def extract_unit_sale_price(text: str) -> ExtractedField | None:
    m = re.search(
        r"\b(?:unit\s*(?:sale\s*)?price|price\s*per\s*(?:kg|g|litre|l|ml))\b\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)",
        text, re.IGNORECASE,
    )
    if not m:
        return None
    return ExtractedField(
        field_name="unit_sale_price",
        value=m.group(1),
        numeric=float(m.group(1)),
        confidence=0.9,
        source_text=m.group(0),
    )


def extract_dates(text: str) -> list:
    """Extract all dates with rough classification."""
    out = []
    for rx in _DATE_RES:
        for m in rx.finditer(text):
            out.append({"raw": m.group(0)})
    # de-dup preserving order
    seen = set()
    uniq = []
    for d in out:
        if d["raw"] not in seen:
            seen.add(d["raw"])
            uniq.append(d)
    return uniq


def extract_typed_dates(text: str) -> dict:
    """Extract typed date fields (packing_date, best_before_date, expiry_date).

    Uses label keywords to assign each found date to the matching field.
    """
    result = {}
    label_map = {
        "packing_date": [r"\b(?:packed|packing|pack\s*dt|m\.?f\.?g|mfg\.?|m\.?f\.?d\.?|manufactur|prod\.?|production)\b[^0-9A-Za-z]*(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|[A-Za-z]{3,9}\s*\d{4})\b", r"\b(?:packed|packing|m\.?f\.?g|mfg\.?|m\.?f\.?d\.?)\b[^0-9A-Za-z]*(\d{1,2})\b"],
        "best_before_date": [r"\b(?:best\s*before|best-by|best by)\b[^0-9]*(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|[A-Za-z]{3,9}\s*\d{4}|\d{1,2}\s*(?:month|days?|year)s?\s*(?:from|of))"],
        "expiry_date": [r"\b(?:expiry|exp\.?|expires?\s*on|use\s*by)\b[^0-9]*(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|[A-Za-z]{3,9}\s*\d{4})"],
    }
    for field, res in label_map.items():
        for rx in res:
            m = re.search(rx, text, re.IGNORECASE)
            if m:
                result[field] = m.group(1).strip()
                break
    return result


def extract_country_of_origin(text: str) -> ExtractedField | None:
    """'Made in India', 'Country of Origin: India', 'Product of India', etc."""
    m = re.search(
        r"\b(?:country\s*of\s*origin|origin)\b\s*[:\-]?\s*([A-Za-z][A-Za-z ]{1,19}|\b(?:india|china|usa|u\.?s\.?a\.?|uk|u\.?k\.?|germany|japan|korea|vietnam|thailand|malaysia|bangladesh|pakistan|sri\s*lanka|nepal|bhutan)\b)",
        text, re.IGNORECASE,
    )
    if not m:
        # OCR frequently merges "Made in India" -> "Madein India", "Made InIndia"
        m = re.search(
            r"\b(?:made\s*in|madein|product\s+of|productof|packed\s+in)\s*:?\s*([A-Za-z][A-Za-z ]{1,19})",
            text, re.IGNORECASE,
        )
    if m:
        country = m.group(1).strip()
        return ExtractedField(
            field_name="country_of_origin",
            value=country,
            confidence=0.8,
            source_text=m.group(0),
        )
    return None


def extract_batch_number(text: str) -> ExtractedField | None:
    """'Batch No: BN-2601', 'LOT NO. 23045', 'B.No. 12'."""
    m = re.search(
        r"\b(?:batch\s*(?:no\.?|number|id)?|lot\s*(?:no\.?|number)?|b\.?\s*n\.?)\s*[:\-]?_?\s*([A-Za-z]{1,4}[\d\-_/][A-Za-z0-9\-_/]{1,15}|\d[\dA-Za-z\-_/]{1,15})",
        text, re.IGNORECASE,
    )
    if m:
        return ExtractedField(
            field_name="batch_number",
            value=m.group(1).strip(),
            confidence=0.8,
            source_text=m.group(0),
        )
    return None


def extract_manufacturer_name(text: str) -> ExtractedField | None:
    # "Mfd. by ABC Foods", "Manufactured by ...", "Packed by ...", "Marketed by ..."
    # Name stops at end-of-line or before an address/city keyword on the SAME line.
    m = re.search(
        r"\b(?:mfd\.?\s*by|manufactur(?:ed|er)\s*[:\-]?\s*by|pack(?:ed|er)?\s*[:\-]?\s*by|marketed\s*by)\s+([A-Za-z][A-Za-z0-9&\'\. ]+?)(?=$|\n|\b(?:plot|near|delhi|mumbai|bangalore|bengaluru|chennai|kolkata|hyderabad|pune|ahmedabad|india)\b)",
        text, re.IGNORECASE | re.MULTILINE,
    )
    if m:
        name = m.group(1).strip()
        return ExtractedField(
            field_name="manufacturer_name",
            value=name,
            confidence=0.85,
            source_text=m.group(0),
        )
    # "Manufactured by:" sits alone at end of line; the company name follows on
    # the NEXT line ("...:\nFreshGlow Products Pvt. Ltd."). Capture the next line.
    m = re.search(
        r"\b(?:mfd\.?\s*by|manufactur(?:ed|er)\s*[:\-]?\s*by|pack(?:ed|er)?\s*[:\-]?\s*by|marketed\s*by)\s*:?\s*\n\s*([A-Z][^\n]+)",
        text, re.IGNORECASE | re.MULTILINE,
    )
    if m:
        name = m.group(1).strip()
        # strip leading company suffix ambiguities and trailing punctuation
        name = re.split(r"\s*(?:plot|industrial\s+area|near|road|street)\b", name, flags=re.IGNORECASE)[0].strip()
        name = name.rstrip(":;,._ ")
        return ExtractedField(
            field_name="manufacturer_name",
            value=name,
            confidence=0.8,
            source_text=m.group(0),
        )
    return None


def extract_manufacturer_address(text: str) -> ExtractedField | None:
    """Best-effort address capture:
    - after a 'Mfd. by <name>' line, the next line(s) until a boundary keyword
    - or lines containing 'Plot', 'Near', 'Road', 'Street', 'Industrial Area',
      'Tehsil', 'District', 'P.O.', 'Pin', a city name, etc.
    """
    # Address on the line(s) right after a manufacturer line
    m = re.search(
        r"\b(?:mfd\.?\s*by|manufactur(?:ed|er)\s*[:\-]?\s*by|pack(?:ed|er)?\s*[:\-]?\s*by|marketed\s*by)\s+[A-Za-z0-9&\'\. ]+?\n([^\n]+)",
        text, re.IGNORECASE,
    )
    if m:
        addr = m.group(1).strip()
        if len(addr) >= 8:
            return ExtractedField(
                field_name="manufacturer_address",
                value=addr,
                confidence=0.7,
                source_text=m.group(0),
            )
    # Standalone address-looking line
    m = re.search(
        r"^\s*(?:plot\s*\d+|near\s+|house\s*no\.?|h\.?no\.?|street|road|industrial\s+area|s\.?o\.?|village|post\s*office|p\.?o\.?)([^\n]*)$",
        text, re.IGNORECASE | re.MULTILINE,
    )
    if m:
        addr = m.group(0).strip()
        return ExtractedField(
            field_name="manufacturer_address",
            value=addr,
            confidence=0.6,
            source_text=m.group(0),
        )
    return None


def extract_consumer_care(text: str) -> ExtractedField | None:
    """Consumer care contact: look for contact markers + phone/email/website."""
    found = {}
    for key, rx in _CONTACT_RES.items():
        m = rx.search(text)
        if m:
            found[key] = m.group(0)
    # Only count if near a care/contact marker or it's a standalone phone/email
    has_marker = re.search(r"\b(customer\s*care|consumer\s*care|cust\.?\s*care|helpline|toll\s*free|contact)\b", text, re.IGNORECASE)
    if found and (has_marker or "phone" in found or "email" in found or "website" in found):
        details = ", ".join(f"{k}: {v}" for k, v in found.items())
        return ExtractedField(
            field_name="consumer_care_contact",
            value=details,
            confidence=0.8 if has_marker else 0.6,
            source_text=details,
        )
    return None


def extract_commodity_name(text: str) -> ExtractedField | None:
    """Best-effort commodity name.

    Priority:
    1. Explicit 'Commodity Name:' / 'Product Name:' label
    2. First non-label text line (heuristic)
    """
    # Explicit label — tolerant of common OCR typos (Commedity, Commdity...)
    m = re.search(
        r"\b(comm[a-z]*dity|product)\s*name\b\s*:?\s*([A-Za-z][^|\n]{2,60})",
        text, re.IGNORECASE,
    )
    if m:
        name = m.group(2).strip()
        # Strip OCR residue: trailing "{...}" noise and FSSAI-style category
        # codes like "7.0 Bakery Wares, 7.2.1 {Biscuits)"
        name = re.sub(r"\s*\{.*$", "", name)
        name = re.split(r"\s+\d+\.\d+[\d.]*\s+\w", name)[0]
        name = re.split(r"\b(Wares?|Products?)\s*$", name)[0].strip()
        return ExtractedField(
            field_name="commodity_name",
            value=name,
            confidence=0.85,
            source_text=m.group(0),
        )
    # Heuristic: first line that isn't an obvious label keyword line.
    # To avoid the lenient text-pass (low-confidence OCR concatenation),
    # only accept a candidate that is a reasonable length and mostly letters.
    lines = [l for l in text.splitlines() if l.strip() and not re.search(r"\b(mrp|net wt|net weight|mfd|packed|customer care|consumer care|best before|use by|batch|lot no|ingredients)\b", l, re.IGNORECASE)]
    for candidate in lines:
        cand = candidate.strip()
        if not cand:
            continue
        words = cand.split()
        # Reject long garbage runs and mostly-numeric strings
        if len(cand) > 60:
            continue
        letters = sum(1 for ch in cand if ch.isalpha())
        if letters < len(words) * 2:
            continue
        return ExtractedField(
            field_name="commodity_name",
            value=cand,
            confidence=0.6,
            source_text=cand,
        )
    return None


def run_extraction(raw_text: str) -> ExtractionResult:
    """Run all extractors over the combined OCR text."""
    text = _clean_text(raw_text)
    result = ExtractionResult(raw_text=text)

    def add(field: ExtractedField | None):
        if field:
            result.fields[field.field_name] = field

    add(extract_net_quantity(text))
    add(extract_mrp(text))
    add(extract_unit_sale_price(text))
    add(extract_manufacturer_name(text))
    add(extract_manufacturer_address(text))
    add(extract_consumer_care(text))
    add(extract_commodity_name(text))
    add(extract_country_of_origin(text))
    add(extract_batch_number(text))

    # Dates are stored as typed fields plus a combined list
    typed_dates = extract_typed_dates(text)
    for field_name, val in typed_dates.items():
        result.fields[field_name] = ExtractedField(
            field_name=field_name,
            value=val,
            confidence=0.85,
            source_text=field_name,
        )
    raw_dates = extract_dates(text)
    result.fields["dates"] = ExtractedField(
        field_name="dates",
        value=", ".join(d["raw"] for d in raw_dates) or None,
        confidence=0.8 if raw_dates else 0.0,
        source_text="",  # handled separately
    )

    # generic_name is a rule-level alias for commodity_name; sync it if present
    if "commodity_name" in result.fields and "generic_name" not in result.fields:
        cn = result.fields["commodity_name"]
        result.fields["generic_name"] = ExtractedField(
            field_name="generic_name",
            value=cn.value,
            confidence=cn.confidence,
            source_text=cn.source_text,
        )

    return result


def extraction_to_dict(result: ExtractionResult) -> dict:
    """Convert ExtractionResult into a serializable dict of field metadata."""
    return {
        name: {
            "value": f.value,
            "numeric": f.numeric,
            "unit": f.unit,
            "confidence": f.confidence,
            "source_text": f.source_text,
        }
        for name, f in result.fields.items()
    }
