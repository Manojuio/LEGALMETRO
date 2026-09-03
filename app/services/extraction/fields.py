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
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)?\s*:?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*(?:Rs\.?|INR|₹)\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMax\.?\s*Retail\s+Price\s*(?:Rs\.?|INR|₹)?\s*:?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bM{1,2}[RPI]{1,2}[PI]?\s*(?:Rs\.?|INR|₹)\s*:?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bMRP\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE),
    # MRP followed by a stray symbol OCR misreads of ₹/Rs as < > { ( | etc.
    re.compile(r"\bMRP\s*[:\-]?\s*[<>{(\[\]\|`'\"~@#&*]+\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE),
    # M.R.P. disfigurement regardless of symbol noise
    re.compile(r"\bM\.?R\.?P\.?\s*:?\s*(?:Rs\.?|INR|₹)?\s*[<>{(\[\]\|`'\"~@#&*]*(\d+(?:\.\d+)?)\b", re.IGNORECASE),
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
_PRICE_VALUE_RE = re.compile(
    r"(?:[\s:₹Rrs.]|^)(\d{1,4}(?:\.\d{1,2})?)(?!\s*(?:g|gm|gms|gram|kg|kg\.|ml|l|lit|litre|nos|pcs|count|pc|no|nos\b|mg)\b)",
    re.IGNORECASE,
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

def _extract_mrp(col, text, image_id):
    for rx in _MRP_RES:
        m = rx.search(text)
        if m:
            val = float(m.group(1))
            _add(col, _ev("mrp", f"{val:g}", m.group(0), image_id, 0.95, numeric=val))
            return
    # Boxed-labels fallback: heading ("MRP") and value ("120") are spatially
    # separated (heading printed outside the box, value inside). When the
    # adjacent regex found nothing but the MRP label IS present, bind the first
    # standalone price-like number within a short window after the label.
    lm = _MRP_LABEL_RE.search(text)
    if lm:
        window = text[lm.end():lm.end() + 80]
        pm = _PRICE_VALUE_RE.search(window)
        if pm:
            val = float(pm.group(1))
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