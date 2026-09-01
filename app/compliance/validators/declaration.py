"""Rule validators — deterministic checks producing PASS/FAIL/REVIEW/NOT_APPLICABLE.

Each validator receives the structured extraction result and returns a
RuleResult-compatible dict. Validators NEVER use an LLM. They only evaluate
structured evidence produced by the extraction service.
"""

from dataclasses import dataclass

from app.services.extraction_service import ExtractionResult


class Status:
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ValidationOutcome:
    status: str
    reason: str
    evidence: list = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


def _field_present(extraction: ExtractionResult, names: list[str]) -> ValidationOutcome:
    """Generic FIELD_PRESENT validator."""
    missing = [n for n in names if not extraction.has(n)]
    if not missing:
        return ValidationOutcome(
            Status.PASS,
            f"Required declaration(s) present: {', '.join(names)}",
            confidence=0.95,
        )
    return ValidationOutcome(
        Status.FAIL,
        f"Required declaration(s) not detected: {', '.join(missing)}",
        evidence=[{"type": "field", "missing": missing}],
        confidence=0.9,
    )


def validate_field_present(extraction: ExtractionResult, fields: list[str]) -> ValidationOutcome:
    return _field_present(extraction, fields)


def validate_quantity_unit(extraction: ExtractionResult) -> ValidationOutcome:
    """Rule 12 — net quantity must use SI units (weight/volume/number)."""
    nq = extraction.get("net_quantity")
    if nq is None:
        return ValidationOutcome(
            Status.FAIL,
            "Net quantity not detected — cannot validate unit",
            evidence=[{"type": "field", "missing": ["net_quantity"]}],
            confidence=0.85,
        )
    if nq.unit is None:
        # Net-weight label seen but OCR couldn't read value/unit reliably
        return ValidationOutcome(
            Status.REVIEW,
            "Net quantity label detected but value/unit not readable "
            "reliably from image — requires human review",
            evidence=[{"type": "field", "field": "net_quantity", "partial": True}],
            confidence=0.4,
        )
    allowed = {"g", "kg", "mg", "ml", "l", "cl", "nos"}
    if nq.unit in allowed:
        return ValidationOutcome(
            Status.PASS,
            f"Net quantity '{nq.value}' uses acceptable SI unit ({nq.unit})",
            evidence=[{"type": "field", "field": "net_quantity", "value": nq.value, "unit": nq.unit}],
            confidence=0.95,
        )
    return ValidationOutcome(
        Status.FAIL,
        f"Net quantity unit '{nq.unit}' is not an approved SI unit",
        evidence=[{"type": "field", "field": "net_quantity", "unit": nq.unit}],
        confidence=0.9,
    )


def validate_standard_quantity(extraction: ExtractionResult, category: str) -> ValidationOutcome:
    """Rule 13 — quantity should match a standard package value.

    Uses numeric value normalized (g/ml). Compare against the category-specific
    standard if available, else the generic standard set.
    """
    nq = extraction.get("net_quantity")
    if nq is None or nq.unit is None:
        return ValidationOutcome(
            Status.REVIEW,
            "Net quantity value/unit not readable — standard quantity "
            "cannot be verified from image",
            evidence=[{"type": "field", "field": "net_quantity", "partial": True}],
            confidence=0.4,
        )

    # Load category-specific standards if we have the mapping
    standards = _load_standard_values(category, nq.unit)
    if nq.numeric is None:
        return ValidationOutcome(Status.REVIEW, "Net quantity value not numeric")

    # tolerance within 5% to allow declaration differences
    tol = nq.numeric * 0.05
    for std in standards:
        if abs(nq.numeric - std) <= tol:
            return ValidationOutcome(
                Status.PASS,
                f"Net quantity {nq.value} matches a standard package quantity",
                evidence=[{"type": "standard", "value": nq.numeric, "unit": nq.unit, "match": std}],
                confidence=0.85,
            )
    return ValidationOutcome(
        Status.REVIEW,
        f"Net quantity {nq.value} does not match a listed standard package quantity",
        evidence=[{"type": "standard", "value": nq.numeric, "unit": nq.unit}],
        confidence=0.7,
    )


def _load_standard_values(category: str, unit: str) -> list[float]:
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent.parent.parent / "rules" / "standard_packages.json"
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # category-specific
    cat_key = category if category in data.get("category_specific_standards", {}) else None
    if cat_key:
        cat_std = data["category_specific_standards"][cat_key]
        if unit == cat_std.get("unit"):
            return [float(v) for v in cat_std["standard_values"]]
    # generic by unit family
    for kind, entries in data["standard_packages"].items():
        if unit in entries.get("unit", "") or unit in ("g", "ml"):
            unit_tag = entries.get("unit")
            if kind == "WEIGHT" and unit in ("g", "kg"):
                return [float(v["value"]) * (1000 if unit == "kg" else 1) for v in entries["standards"]]
            if kind == "VOLUME" and unit in ("ml", "l"):
                return [float(v["value"]) * (1000 if unit == "l" else 1) for v in entries["standards"]]
            if kind == "NUMBER" and unit == "nos":
                return [float(v["value"]) for v in entries["standards"]]
    return []


def validate_date_present(extraction: ExtractionResult) -> ValidationOutcome:
    """Rule 15 — at least one date (packing/manufacture/best-before) present.

    Accepts both raw numeric dates ('08/2026') and typed best-before/
    packing declarations ('BEST BEFORE 9 MONTHS FROM PACKAGING').
    """
    typed = ["packing_date", "best_before_date", "expiry_date"]
    found = [f for f in typed if extraction.has(f)]
    dates = extraction.get("dates")
    if found:
        return ValidationOutcome(
            Status.PASS,
            f"Date/declaration detected: {', '.join(found)}"
            + (f" ({dates.value})" if dates and dates.value else ""),
            evidence=[{"type": "field", "fields": found}],
            confidence=0.85,
        )
    if dates and dates.value:
        return ValidationOutcome(
            Status.PASS,
            f"Date(s) detected: {dates.value}",
            evidence=[{"type": "field", "field": "dates", "value": dates.value}],
            confidence=0.9,
        )
    return ValidationOutcome(
        Status.FAIL,
        "No manufacturing/packing date detected",
        evidence=[{"type": "field", "missing": ["dates"]}],
        confidence=0.85,
    )


def validate_price_present(extraction: ExtractionResult) -> ValidationOutcome:
    """Rule 3/6 — MRP / retail sale price present."""
    if extraction.has("mrp"):
        mrp = extraction.get("mrp")
        return ValidationOutcome(
            Status.PASS,
            f"MRP detected: {mrp.value}",
            evidence=[{"type": "field", "field": "mrp", "value": mrp.value}],
            confidence=0.95,
        )
    if extraction.has("unit_sale_price"):
        return ValidationOutcome(Status.PASS, "Unit sale price detected, MRP not explicitly present", confidence=0.7)
    return ValidationOutcome(
        Status.FAIL,
        "MRP / retail sale price not detected",
        evidence=[{"type": "field", "missing": ["mrp"]}],
        confidence=0.85,
    )


def validate_manufacturer_present(extraction: ExtractionResult) -> ValidationOutcome:
    """Rules 4/10 — manufacturer/packer/importer details present."""
    if extraction.has("manufacturer_name"):
        return ValidationOutcome(
            Status.PASS,
            f"Manufacturer details detected: {extraction.get('manufacturer_name').value}",
            evidence=[{"type": "field", "field": "manufacturer_name", "value": extraction.get('manufacturer_name').value}],
            confidence=0.9,
        )
    return ValidationOutcome(
        Status.FAIL,
        "Manufacturer/packer/importer details not detected",
        evidence=[{"type": "field", "missing": ["manufacturer_name"]}],
        confidence=0.85,
    )


def validate_consumer_care_present(extraction: ExtractionResult) -> ValidationOutcome:
    """Rules 11/22 — consumer care contact present."""
    if extraction.has("consumer_care_contact"):
        contact = extraction.get("consumer_care_contact")
        return ValidationOutcome(
            Status.PASS,
            f"Consumer care contact detected: {contact.value}",
            evidence=[{"type": "field", "field": "consumer_care_contact", "value": contact.value}],
            confidence=contact.confidence,
        )
    return ValidationOutcome(
        Status.FAIL,
        "Consumer complaint/contact details not detected",
        evidence=[{"type": "field", "missing": ["consumer_care_contact"]}],
        confidence=0.8,
    )


def validate_contact_any_of(extraction: ExtractionResult) -> ValidationOutcome:
    """Rule 11 — at least ONE of consumer_care_contact / phone / email / website.

    Legal requirement is 'at least one'. The generic FIELD_PRESENT validator
    would incorrectly require ALL contact fields.
    """
    candidates = [
        "consumer_care_contact",
        "consumer_care_phone",
        "consumer_care_email",
        "consumer_care_website",
    ]
    present = [c for c in candidates if extraction.has(c)]
    if present:
        return ValidationOutcome(
            Status.PASS,
            f"Consumer care contact detected ({', '.join(present)})",
            evidence=[{"type": "field", "fields": present}],
            confidence=0.9,
        )
    return ValidationOutcome(
        Status.FAIL,
        "No consumer care contact (phone/email/website) detected",
        evidence=[{"type": "field", "missing": candidates}],
        confidence=0.8,
    )


def validate_commodity_present(extraction: ExtractionResult) -> ValidationOutcome:
    """Rules 5/6 — name of commodity present."""
    if extraction.has("commodity_name"):
        return ValidationOutcome(
            Status.PASS,
            f"Commodity name detected: {extraction.get('commodity_name').value}",
            evidence=[{"type": "field", "field": "commodity_name", "value": extraction.get('commodity_name').value}],
            confidence=0.7,
        )
    return ValidationOutcome(
        Status.FAIL,
        "Name of commodity not detected",
        evidence=[{"type": "field", "missing": ["commodity_name"]}],
        confidence=0.7,
    )


def validate_physical_test(rule_id: str) -> ValidationOutcome:
    """Rules 19/20 — physical sampling/testing required. NEVER auto-decided."""
    return ValidationOutcome(
        Status.NOT_APPLICABLE,
        "Physical quantity verification requires sampling and testing "
        "— cannot be determined from image alone (Rule 19/20).",
        evidence=[{"type": "physical_test_required"}],
        confidence=1.0,
    )


def validate_visual_review() -> ValidationOutcome:
    """Visual rules (7/8/9) — approximated by CV; return REVIEW by default.

    Font size, placement, and legibility cannot be reliably measured from a
    single arbitrary photo. Without a reliable CV measurement, we return
    REVIEW rather than guessing PASS/FAIL.
    """
    return ValidationOutcome(
        Status.REVIEW,
        "Visual assessment (font size / placement / legibility) requires "
        "reliable measurement; image-only estimate is inconclusive.",
        evidence=[{"type": "visual", "basis": "image_only"}],
        confidence=0.6,
    )
