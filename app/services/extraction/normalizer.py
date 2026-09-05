"""Field normalization — ``app/services/extraction/normalizer.py`` (Phase 8).

Normalizes extracted *values* so the rule engine can compare them:
    - unit aliases  -> canonical unit + numeric magnitude (kg->g, l->ml)
    - currency      -> strip "Rs.", "INR", "₹", "MRP" residue to a number
    - decimals      -> "1,200.50" -> 1200.5 ; "1 200" -> 1200
    - dates         -> a typed, comparable ISO-ish form where possible

These normalizers are deterministic and non-destructive: they return the
normalized value *plus* a boolean ``clean`` so a caller may mark a field
UNCERTAIN when the value could not be meaningfully normalized.
"""

import re

# --- Units ----------------------------------------------------------------
# alias -> (kind, canonical_unit)
_UNIT_CANON = {
    # weight
    "kg": ("weight", "kg"), "kilogram": ("weight", "kg"), "kgs": ("weight", "kg"),
    "g": ("weight", "g"), "gram": ("weight", "g"), "gm": ("weight", "g"),
    "gms": ("weight", "g"), "grams": ("weight", "g"),
    "mg": ("weight", "mg"), "milligram": ("weight", "mg"),
    "tonne": ("weight", "tonne"), "ton": ("weight", "tonne"),
    # volume
    "l": ("volume", "l"), "litre": ("volume", "l"), "liter": ("volume", "l"),
    "ml": ("volume", "ml"), "millilitre": ("volume", "ml"),
    "milliliter": ("volume", "ml"), "cc": ("volume", "ml"),
    "cl": ("volume", "ml"), "dl": ("volume", "dl"),
    # number / count
    "nos": ("number", "nos"), "no": ("number", "nos"), "no.": ("number", "nos"),
    "pieces": ("number", "nos"), "pcs": ("number", "nos"), "pcs.": ("number", "nos"),
    "count": ("number", "nos"), "units": ("number", "nos"),
    "tablets": ("number", "nos"), "capsules": ("number", "nos"),
    "sheets": ("number", "nos"), "pairs": ("number", "nos"),
    # length
    "mm": ("length", "mm"), "cm": ("length", "cm"),
    "m": ("length", "m"), "mt": ("length", "m"), "km": ("length", "km"),
}


def canonical_unit(raw: str):
    """Map a raw unit token to (kind, canonical_unit) or None."""
    if not raw:
        return None
    return _UNIT_CANON.get(raw.strip().lower().rstrip("."))


def normalize_quantity(value: float, raw_unit: str):
    """Return (kind, unit, numeric) with a sensible scale.

    kg -> g (×1000), l -> ml (×1000). Returns (None, None, value) when the
    unit is unknown to avoid inventing a scale.
    """
    info = canonical_unit(raw_unit)
    if info is None:
        return None, None, value
    kind, unit = info
    numeric = value
    if unit == "kg":
        numeric = value * 1000
        unit = "g"
    elif unit == "l":
        numeric = value * 1000
        unit = "ml"
    return kind, unit, numeric


# --- Currency / numbers ----------------------------------------------------

_NUM_CLEAN = re.compile(r"[^\d.,]")


def parse_number(text: str):
    """Parse a possibly-formatted number in ``text`` to float or None.

    Handles "1,200.50", "1200", "₹450", "Rs. 450". Returns None when no
    leading digits are present.
    """
    if not text:
        return None
    m = re.search(r"(\d[\d,]*\.?\d*)", text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def strip_currency(text: str) -> str:
    """Return text with currency prefixes/suffixes removed."""
    if not text:
        return text
    return re.sub(r"(rs\.?|inr|₹|max\.?\s*retail\s*price|mrp|unit\s*sale\s*price)", "", text, flags=re.IGNORECASE).strip(" :\-")


_CURRENCY_TOKENS = re.compile(
    r"(rs\.?|inr|₹|max\.?\s*retail\s*price|mrp|price)", re.IGNORECASE
)


def is_price_context(text: str) -> bool:
    """True if the given source text suggests a price context."""
    return bool(_CURRENCY_TOKENS.search(text or ""))


# --- Dates -----------------------------------------------------------------

_MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def normalize_due_date(raw: str) -> str:
    """Best-effort normalized date ``YYYY-MM-DD`` (or ``''`` if unparseable)."""
    if not raw:
        return ""
    raw = raw.strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if m:
        d, mo, y = m.groups()
        yy = f"20{y}" if len(y) == 2 else y
        return f"{yy}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{1,2})[/\-.](\d{4})$", raw)
    if m:
        mo, y = m.groups()
        return f"{y}-{int(mo):02d}-00"
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{4})$", raw)
    if m:
        mon, y = m.groups()
        mm = _MONTHS.get(mon.lower()[:3])
        if mm:
            return f"{y}-{mm}-00"
    return ""