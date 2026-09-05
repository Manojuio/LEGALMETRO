"""Deterministic field extraction — ``app/services/extraction/fields.py`` (Phase 7).

Runs the ported regex extractors over **reconstructed semantic lines**, so a
field can carry its source image, bbox, and OCR confidence — full evidence
traceability. Each extractor returns a :class:`FieldEvidence`.

The extractors are copied verbatim from the legacy ``extraction_service.py``
(regexes proven on the project fixture dataset) and adapted to run per line
and to emit evidence/status instead of a bare value.

This module never decides compliance. It only produces structured evidence.
"""

import re

from app.services.extraction.evidence import FieldEvidence, FieldStatus
from app.services.extraction import normalizer as norm


# ---------------------------------------------------------------------------
# MRP / price
# ---------------------------------------------------------------------------
_MRP_RES = [
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)?\s*:?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMax\w*\.?\s*Retail\s+Price\s*:?\s*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bM{1,2}[RPI]{1,2}[PI]?\s*(?:Rs\.?|INR|₹)\s*:?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
    # MRP followed by a stray symbol OCR misreads of ₹/Rs as < > { ( | etc.
    re.compile(r"\bMRP\s*[:\-]?\s*[<>{(\[\]\|`'\"~@#&*]+\s*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
    # M.R.P. disfigurement regardless of symbol noise
    re.compile(r"\bM\.?R\.?P\.?\s*:?\s*(?:Rs\.?|INR|₹)?\s*[<>{(\[\]\|`'\"~@#&*]*(\d[\d,]*(?:\.\d+)?)\b", re.IGNORECASE),
]

# Boxed-labels support: the printed heading ("MRP") often sits OUTSIDE a box
# while the value ("₹120") is printed INSIDE it, so label and value land on
# different lines / separated by whitespace. These regexes power a fallback
# that binds the nearest standalone price-like number to the MRP label.
_MRP_LABEL_RE = re.compile(
    r"\b(?:max\.?\s*retail\s*price|m\.?r\.?p\.?)\b", re.IGNORECASE
)
# A standalone price-like value: 1-4 digit integer or decimal, and NOT followed
# by / preceded by a quantity unit (so "120 g" is not mistaken for a price).
# Expanded unit list to prevent false MRP extraction from net-quantity and
# other non-price numeric values.
_PRICE_VALUE_RE = re.compile(
    r"(?:[\s:₹Rrs.]|^)(\d{1,4}(?:\.\d{1,2})?)"
    r"(?!\s*(?:g|gm|gms|grams?|kg|kg\.|ml|l|lit|litre|liter|litres?|liters?|"
    r"nos?\.?|pcs?\.?|pieces?|count|pc|mg|milligram|"
    r"tonne|ton|cl|dl|cm|mm|mt|km|months?|days?|years?|packs?|bottles?|cans?|"
    r"sheets?|tablets?|capsules?|pairs?|units?)\b)",
    re.IGNORECASE,
)

# Patterns that look numeric but are NOT prices — phone numbers, PIN codes,
# dates, batch-like sequences, FSSAI/license numbers.  Used to reject
# candidates from the boxed-labels fallback when the surrounding context is
# clearly non-price.
_NON_PRICE_RE = re.compile(
    r"(?:"
    r"\d{7,}"                    # 7+ digits → phone, PIN, barcode, licence
    r"|(?<!\d)\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?!\d)"  # date-like DD/MM/YYYY
    r"|(?<!\d)\d{1,2}[/-]\d{4}(?!\d)"                 # date-like MM/YYYY
    r")"
)

# Indian phone number pattern (10-digit mobile, 11-digit toll-free).
_INDIAN_PHONE_RE = re.compile(
    r"(?:\+?91[\s\-]?)?\d{5}[\s\-]?\d{5}"  # 10-digit with optional +91
    r"|1800[\s\-]?\d{3,4}[\s\-]?\d{3,4}"    # toll-free 1800-xxx-xxxx
)

_UNIT_PATTERN = (
    r"(kg\.?|gms?\.?|g\b|grams?|mg\b|milligram|ml\b|cl\b|dl\b|lit(?:re|er)s?|"
    r"l\b|nos\.?|pcs\.?|pieces?|tablets?|capsules?|sheets?|pairs?|cm|mm|m\b|%|tonne|ton)"
)

_NET_QTY_RE = re.compile(
    r"\b(?:net\s*(?:wt\.?|weight|qty\.?|quantity|contents?)?|nel\s*(?:conlent|content|qty)|n\.?\s*w\.?)\s*[:\-]?\s*"
    r"(\d+(?:\.\d+)?)\s*" + _UNIT_PATTERN + r"\b",
    re.IGNORECASE,
)
_NET_QTY_LABEL_RE = re.compile(
    r"\bnet\s*(?:wt\.?|weight|qty\.?|quantity|contents?)\b", re.IGNORECASE
)

_UNIT_SALE_PRICE_RE = re.compile(
    r"\b(?:unit\s*(?:sale\s*)?price|price\s*per\s*(?:kg|g|litre|l|ml))\b\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Dates
_DATE_RE = re.compile(
    r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b|\b(\d{1,2})[/\-.](\d{4})\b|"
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})\b",
    re.IGNORECASE,
)

_DATE_LABEL_MAP = {
    "packing_date": re.compile(
        r"\b(?:packed|packing|pack\s*dt|m\.?f\.?g|mfg\.?|m\.?f\.?d\.?|manufactur|prod\.?|production)\b[^0-9A-Za-z]*"
        r"(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|[A-Za-z]{3,9}\s*\d{4}|\d{1,2})\b",
        re.IGNORECASE,
    ),
    "best_before_date": re.compile(
        r"\b(?:best\s*before|best-by|best by)\b[^0-9]*"
        r"(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|"
        r"[A-Za-z]{3,9}\s*\d{4}|\d{1,2}\s*(?:month|days?|year)s?\s*(?:from|of))",
        re.IGNORECASE,
    ),
    "expiry_date": re.compile(
        r"\b(?:expiry|exp\.?|expires?\s*on|use\s*by)\b[^0-9]*"
        r"(\d{1,2}[/\-.]\d{2,4}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|[A-Za-z]{3,9}\s*\d{4})",
        re.IGNORECASE,
    ),
}

_COUNTRY_RE = re.compile(
    r"\b(?:country\s*of\s*origin|origin)\b\s*[:\-]?\s*"
    r"([A-Za-z][A-Za-z ]{1,19}|\b(?:india|china|usa|u\.?s\.?a\.?|uk|u\.?k\.?|germany|japan|"
    r"korea|vietnam|thailand|malaysia|bangladesh|pakistan|sri\s*lanka|nepal|bhutan)\b)",
    re.IGNORECASE,
)
_COUNTRY_MADE_IN_RE = re.compile(
    r"\b(?:made\s*in|madein|product\s+of|productof|packed\s+in)\s*:?\s*([A-Za-z][A-Za-z ]{1,19})",
    re.IGNORECASE,
)

_BATCH_RE = re.compile(
    r"\b(?:batch\s*(?:no\.?|number|id)?|lot\s*(?:no\.?|number)?|b\.?\s*n\.?)\s*[:\-]?_?\s*"
    r"([A-Za-z]{1,4}[\d\-_/][A-Za-z0-9\-_/]{1,15}|\d[\dA-Za-z\-_/]{1,15})",
    re.IGNORECASE,
)

# Tolerant manufacturer/marketer generic lines. OCR routinely garbles these
# ("Manufactured" -> "Manulactured", "Marketed" -> "Matketed", "Mfd." -> "Mdf"),
# so we anchor on distinctive leading letters + the trailing "by", capturing the
# name that follows on the same or next line.
_MFR_LABEL = (
    r"(?:"
    r"m[fd]\.?\s*by|"                    # Mfd. by / Mdf by / Mfcd by
    r"manu[a-z]{2,12}\s+by|"             # manufactured/manulactured/manufactur by
    r"m[aar][a-z]{2,8}\s+by|"            # marketed/matketed by
    r"pack[a-z]{1,6}\s+by|"              # packed/packing by
    r"market[a-z]{2,6}\s+by"             # marketing/marketd by
    r")"
)

_MANUFACTURER_RE = re.compile(
    r"\b" + _MFR_LABEL + r"\s+"
    r"([A-Za-z][A-Za-z0-9&\'\. ]+?)(?=$|\n|\b(?:plot|near|delhi|mumbai|bangalore|bengaluru|chennai|kolkata|"
    r"hyderabad|pune|ahmedabad|india)\b)",
    re.IGNORECASE | re.MULTILINE,
)

# "Manufactured by:" alone at end of line; company name follows on next line.
_MANUFACTURER_NEXT_LINE_RE = re.compile(
    r"\b" + _MFR_LABEL + r"\s*:?\s*\n\s*([A-Z][^\n]+)",
    re.IGNORECASE | re.MULTILINE,
)

_ADDRESS_NEXT_LINE_RE = re.compile(
    r"\b" + _MFR_LABEL + r"\s+"
    r"[A-Za-z0-9&\'\. ]+?\n([^\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
_ADDRESS_STANDALONE_RE = re.compile(
    r"^\s*(?:plot\s*\d+|near\s+|house\s*no\.?|h\.?no\.?|street|road|industrial\s+area|"
    r"s\.?o\.?|village|post\s*office|p\.?o\.?)([^\n]*)$",
    re.IGNORECASE | re.MULTILINE,
)

_CONTACT_RES = {
    "phone": re.compile(r"(?:\+?\d[\d\s\-]{7,15}\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "website": re.compile(r"\b(?:www\.)[\w.\-]+\.\w+\b|\bhttps?://[^\s]+\b"),
}
_CARE_MARKER_RE = re.compile(
    r"\b(customer\s*care|consumer\s*care|cust\.?\s*care|helpline|toll\s*free|contact)\b",
    re.IGNORECASE,
)

_COMMODITY_LABEL_RE = re.compile(
    r"\b(comm[a-z]*dity|product)\s*name\b\s*:?\s*([A-Za-z][^|\n]{2,60})",
    re.IGNORECASE,
)
_LABEL_KEYWORD_RE = re.compile(
    r"\b(mrp|net wt|net weight|mfd|packed|customer care|consumer care|best before|use by|batch|lot no|ingredients)\b",
    re.IGNORECASE,
)


def extract_fields(lines: list, image_id: str):
    """Run all extractors over reconstructed lines.

    ``lines`` is a list of TextLine (or dicts with ``text``) ordered
    top-to-bottom. Returns a FieldCollection with one or more FieldEvidence
    per field, attributed to ``image_id``.
    """
    from app.services.extraction.evidence import FieldCollection

    col = FieldCollection(image_id=image_id)
    joined = "\n".join(_line_text(ln) for ln in lines)

    bbox_of = lambda ln: getattr(ln, "y", None) or (
        ln.get("y", 0) if isinstance(ln, dict) else 0
    )
    conf_of = lambda ln: 0.0  # per-line OCR conf aggregated elsewhere

    _extract_net_quantity(col, lines, image_id)
    _extract_mrp(col, joined, image_id)
    _extract_unit_sale_price(col, joined, image_id)
    _extract_manufacturer(col, lines, image_id)
    _extract_consumer_care(col, joined, image_id)
    _extract_commodity(col, joined, image_id)
    _extract_country(col, joined, image_id)
    _extract_batch(col, joined, image_id)
    _extract_dates(col, joined, image_id)

    return col


def _line_text(ln) -> str:
    if isinstance(ln, dict):
        return (ln.get("text") or "").strip()
    return (getattr(ln, "text", "") or "").strip()


def _add(col, ev: FieldEvidence | None):
    if ev is not None:
        col.add(ev)


def _ev(field_name, value, source_text, image_id, confidence, status=FieldStatus.DETECTED, numeric=None, unit=None):
    return FieldEvidence(
        field_name=field_name,
        value=value,
        numeric=numeric,
        unit=unit,
        source_text=source_text,
        image_id=image_id,
        confidence=confidence,
        status=status,
    )


# --- net quantity ----------------------------------------------------------

def _extract_net_quantity(col, lines, image_id):
    for ln in lines:
        text = _line_text(ln)
        m = _NET_QTY_RE.search(text)
        if not m:
            # label present but value unreadable -> UNCERTAIN
            label = _NET_QTY_LABEL_RE.search(text)
            if label:
                _add(col, _ev("net_quantity", None, label.group(0), image_id,
                              0.3, FieldStatus.UNCERTAIN))
                return
            continue
        value = float(m.group(1))
        raw_unit = m.group(2).lower().rstrip(".")
        kind, unit, numeric = norm.normalize_quantity(value, raw_unit)
        if unit is None:
            continue
        _add(col, _ev(
            "net_quantity",
            f"{value:g} {raw_unit}",
            m.group(0), image_id, 0.9,
            numeric=numeric, unit=unit,
        ))
        return


# --- mrp / unit price ------------------------------------------------------

def _try_rupee_recovery(text: str) -> str | None:
    """Try to recover ₹ misread as a leading digit before an MRP label.

    When OCR reads "MRP: ₹650" as "MRP: 7650" (or 3650 etc.), the leading
    digit is actually a mangled ₹ symbol.  We try replacing each leading digit
    with '₹' and returning the first text that matches a primary MRP regex.
    This is LOCALIZED — only called when MRP context is already detected.
    """
    if not text:
        return None
    for rx in _MRP_RES:
        if rx.search(text):
            return None  # primary regex already works, no recovery needed
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


def _is_non_price_candidate(value: str, source_text: str) -> bool:
    """Return True if the candidate value is clearly NOT a price.

    Rejects phone numbers, PIN codes, dates, long numeric sequences, and
    numbers preceded/followed by non-price context markers.
    """
    if _NON_PRICE_RE.search(value):
        return True
    if len(value) >= 7:
        return True
    if _INDIAN_PHONE_RE.search(value):
        return True
    if re.match(r"^\d{6}$", value):
        return True  # Indian PIN code (6 digits)
    return False


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
    # (meaning the ₹ symbol is correctly present, not misread)
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
    recovered_text = text[: match.start()] + recovered_source + text[match.end() :]

    for r2 in _MRP_RES:
        m2 = r2.search(recovered_text)
        if m2:
            return _parse_mrp_value(m2.group(1))
    return None


def _extract_mrp(col, text, image_id):
    # --- Pass 1: primary regex patterns on original text ---
    for rx in _MRP_RES:
        m = rx.search(text)
        if m:
            val = _parse_mrp_value(m.group(1))
            # Post-match ₹ recovery: if no ₹/Rs in source and leading digit
            # is a common ₹ OCR misread (3/7/8/9), try recovery.
            recovered = _try_post_match_recovery(m, text)
            if recovered is not None:
                val = recovered
            _add(col, _ev("mrp", f"{val:g}", m.group(0), image_id, 0.95, numeric=val))
            return

    # --- Pass 2: ₹ symbol recovery — OCR may read ₹ as 3/7/8/9 ---
    recovered = _try_rupee_recovery(text)
    if recovered:
        for rx in _MRP_RES:
            m = rx.search(recovered)
            if m:
                val = _parse_mrp_value(m.group(1))
                _add(col, _ev("mrp", f"{val:g}", m.group(0), image_id, 0.85, numeric=val))
                return

    # --- Pass 3: boxed-labels fallback (heading and value on separate lines) ---
    # Only use when the MRP label IS present and the candidate value is NOT
    # a phone number, PIN code, date, quantity, or other non-price number.
    lm = _MRP_LABEL_RE.search(text)
    if lm:
        window = text[lm.end():lm.end() + 80]
        pm = _PRICE_VALUE_RE.search(window)
        if pm and not _is_non_price_candidate(pm.group(1), window):
            val = _parse_mrp_value(pm.group(1))
            _add(col, _ev("mrp", f"{val:g}", lm.group(0) + " -> " + pm.group(0),
                          image_id, 0.55, numeric=val))
    # no context should not invent MRP; leave MISSING


def _extract_unit_sale_price(col, text, image_id):
    m = _UNIT_SALE_PRICE_RE.search(text)
    if m:
        val = float(m.group(1))
        _add(col, _ev("unit_sale_price", m.group(1), m.group(0), image_id, 0.9, numeric=val))


# --- manufacturer / address -------------------------------------------------

def _extract_manufacturer(col, lines, image_id):
    text = "\n".join(_line_text(ln) for ln in lines)
    m = _MANUFACTURER_RE.search(text)
    if m:
        _add(col, _ev("manufacturer_name", m.group(1).strip(), m.group(0), image_id, 0.85))
    else:
        nm = _MANUFACTURER_NEXT_LINE_RE.search(text)
        if nm:
            name = nm.group(1).strip()
            name = re.split(r"\s*(?:plot|industrial\s+area|near|road|street)\b", name, flags=re.IGNORECASE)[0].strip()
            name = name.rstrip(":;,._ ")
            _add(col, _ev("manufacturer_name", name, nm.group(0), image_id, 0.8))
    # address: line right after a manufacturer line, or a standalone address line
    am = _ADDRESS_NEXT_LINE_RE.search(text)
    if am:
        addr = am.group(1).strip()
        if len(addr) >= 8:
            _add(col, _ev("manufacturer_address", addr, am.group(0), image_id, 0.7))
    else:
        sm = _ADDRESS_STANDALONE_RE.search(text)
        if sm:
            _add(col, _ev("manufacturer_address", sm.group(0).strip(), sm.group(0), image_id, 0.6))


def _extract_consumer_care(col, text, image_id):
    found = {}
    for key, rx in _CONTACT_RES.items():
        m = rx.search(text)
        if m:
            found[key] = m.group(0)
    has_marker = _CARE_MARKER_RE.search(text)
    if found and (has_marker or "phone" in found or "email" in found or "website" in found):
        details = ", ".join(f"{k}: {v}" for k, v in found.items())
        conf = 0.8 if has_marker else 0.6
        _add(col, _ev("consumer_care_contact", details, details, image_id, conf))


def _extract_commodity(col, text, image_id):
    m = _COMMODITY_LABEL_RE.search(text)
    if m:
        name = m.group(2).strip()
        name = re.sub(r"\s*\{.*$", "", name)
        name = re.split(r"\s+\d+\.\d+[\d.]*\s+\w", name)[0]
        name = re.split(r"\b(Wares?|Products?)\s*$", name)[0].strip()
        _add(col, _ev("commodity_name", name, m.group(0), image_id, 0.85))
        return
    for ln in _line_texts_if_not_label(text):
        if len(ln) > 60:
            continue
        words = ln.split()
        letters = sum(1 for ch in ln if ch.isalpha())
        if letters < len(words) * 2:
            continue
        _add(col, _ev("commodity_name", ln, ln, image_id, 0.6))
        return


def _line_texts_if_not_label(text):
    return [
        l for l in text.splitlines()
        if l.strip() and not _LABEL_KEYWORD_RE.search(l)
    ]


def _extract_country(col, text, image_id):
    m = _COUNTRY_RE.search(text)
    if not m:
        m = _COUNTRY_MADE_IN_RE.search(text)
    if m:
        _add(col, _ev("country_of_origin", m.group(1).strip(), m.group(0), image_id, 0.8))


def _extract_batch(col, text, image_id):
    m = _BATCH_RE.search(text)
    if m:
        _add(col, _ev("batch_number", m.group(1).strip(), m.group(0), image_id, 0.8))


# --- dates -----------------------------------------------------------------

def _extract_dates(col, text, image_id):
    raw_dates = []
    for m in _DATE_RE.finditer(text):
        raw = m.group(0)
        if raw not in raw_dates:
            raw_dates.append(raw)
    if raw_dates:
        _add(col, _ev("dates", ", ".join(raw_dates), text[:80], image_id, 0.8))
    # typed dates
    for field_name, rx in _DATE_LABEL_MAP.items():
        m = rx.search(text)
        if m:
            raw = m.group(1).strip()
            _add(col, _ev(field_name, raw, m.group(0), image_id, 0.85))