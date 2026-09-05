"""Regression tests for MRP extraction — false positive prevention + ₹ recovery.

Bug 1: System must NEVER extract MRP from unrelated numbers (phone, PIN, date, qty).
Bug 2: OCR misreading ₹ as 3/7/8/9 must not produce incorrect MRP values.

Covers both the evidence-aware extractor (fields.py) and the legacy extractor
(extraction_service.py).
"""

import pytest

from app.services.extraction_service import ExtractionResult, run_extraction
from app.services.extraction.fields import extract_fields
from app.services.ocr.line_builder import TextLine


def _lines(*texts):
    """Build TextLine list from individual text strings."""
    return [TextLine(text=t, index=i, y=i * 40) for i, t in enumerate(texts)]


# ======================================================================
# CASE 1 — MRP clearly present
# ======================================================================

def test_mrp_with_rupee_symbol():
    """MRP: ₹650 -> 650.00"""
    text = "MRP: ₹650"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    ev = col.best("mrp")
    assert ev is not None and ev.numeric == 650.0


# ======================================================================
# CASE 2 — MRP present with decimal
# ======================================================================

def test_mrp_with_decimal():
    """MRP: ₹650.00 -> 650.0"""
    text = "MRP: ₹650.00"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp").numeric == 650.0


# ======================================================================
# CASE 3 — MRP present with Rs
# ======================================================================

def test_mrp_with_rs():
    """M.R.P. Rs. 650/- -> 650.0"""
    text = "M.R.P. Rs. 650/-"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp").numeric == 650.0


# ======================================================================
# CASE 4 — MRP absent, manufacturer PIN exists -> NOT_DETECTED
# ======================================================================

def test_mrp_absent_pin_code_not_extracted():
    """PIN 500032 must not be extracted as MRP."""
    text = "Manufacturer: ABC Foods\nHyderabad - 500032"
    res = run_extraction(text)
    assert not res.has("mrp")

    col = extract_fields(_lines("Manufacturer: ABC Foods", "Hyderabad - 500032"), "img")
    assert col.best("mrp") is None


# ======================================================================
# CASE 5 — MRP absent, customer-care number exists -> NOT_DETECTED
# ======================================================================

def test_mrp_absent_phone_not_extracted():
    """Customer care 1800-123-4567 must not be extracted as MRP."""
    text = "Customer Care: 1800-123-4567"
    res = run_extraction(text)
    assert not res.has("mrp")

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp") is None


# ======================================================================
# CASE 6 — MRP absent, date exists -> NOT_DETECTED
# ======================================================================

def test_mrp_absent_date_not_extracted():
    """Date of Mfg 04/09/2026 must not be extracted as MRP."""
    text = "Date of Mfg: 04/09/2026"
    res = run_extraction(text)
    assert not res.has("mrp")

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp") is None


# ======================================================================
# CASE 7 — MRP absent, quantity exists -> NOT_DETECTED
# ======================================================================

def test_mrp_absent_quantity_not_extracted():
    """Net Quantity 500 g must not be extracted as MRP."""
    text = "Net Quantity: 500 g"
    res = run_extraction(text)
    assert not res.has("mrp")

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp") is None


# ======================================================================
# CASE 8 — MRP present + unrelated numbers -> correct MRP only
# ======================================================================

def test_mrp_present_with_unrelated_numbers():
    """MRP: ₹650 alongside phone and PIN -> only 650 extracted."""
    text = "MRP: ₹650\nCustomer Care: 1800-123-4567\nPIN: 500032"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines("MRP: ₹650", "Customer Care: 1800-123-4567", "PIN: 500032"), "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0
    assert mrp.source_text == "MRP: ₹650"


# ======================================================================
# CASE 9 — Rupee symbol misread as digit
# ======================================================================

def test_rupee_symbol_misread_as_7():
    """OCR returns 'MRP: 7650' for actual ₹650 -> should recover 650."""
    text = "MRP: 7650"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0


def test_rupee_symbol_misread_as_3():
    """OCR returns 'MRP: 3650' for actual ₹650 -> should recover 650."""
    text = "MRP: 3650"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0


def test_rupee_symbol_misread_as_8():
    """OCR returns 'MRP: 8650' for actual ₹650 -> should recover 650."""
    text = "MRP: 8650"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0

    col = extract_fields(_lines(text), "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0


def test_rupee_symbol_misread_with_rs():
    """OCR returns 'MRP Rs. 7120' for actual ₹120 -> should recover 120."""
    text = "MRP Rs. 7120"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 120.0


# ======================================================================
# CASE 10 — No MRP context ("Price 650" without explicit MRP label)
# ======================================================================

def test_price_label_without_mrp_not_extracted():
    """'Price 650' without MRP/M.R.P./Max Retail Price -> NOT_DETECTED."""
    text = "Price 650"
    res = run_extraction(text)
    assert not res.has("mrp")

    col = extract_fields(_lines(text), "img")
    assert col.best("mrp") is None


# ======================================================================
# Unrelated fields remain unchanged
# ======================================================================

def test_unrelated_fields_not_affected_by_mrp_changes():
    """Other extractors must not be affected by MRP extraction changes."""
    text = (
        "Premium Tea\n"
        "Net Wt. 500 g\n"
        "MRP Rs. 450\n"
        "Mfd. by ABC Foods Pvt Ltd\n"
        "Plot 12, Industrial Area, Delhi\n"
        "Made in India\n"
        "Batch No: BN-2601\n"
        "Packed: 08/2026\n"
        "Best Before: 24 months\n"
        "Customer Care: 1800-123-456\n"
    )
    res = run_extraction(text)
    assert res.get("net_quantity").numeric == 500.0
    assert res.get("net_quantity").unit == "g"
    assert res.get("mrp").numeric == 450.0
    assert "ABC Foods" in res.get("manufacturer_name").value
    assert "Delhi" in res.get("manufacturer_address").value
    assert res.get("country_of_origin").value == "India"
    assert res.get("batch_number").value == "BN-2601"
    assert res.get("consumer_care_contact").value
    assert res.get("commodity_name").value == "Premium Tea"


# ======================================================================
# Evidence-aware extractor: same checks
# ======================================================================

def test_evidence_extractor_mrp_present_with_pin_and_phone():
    """Evidence-aware extractor: MRP present -> only correct value extracted."""
    lines = _lines(
        "MRP: ₹650",
        "Customer Care: 1800-123-4567",
        "PIN: 500032",
    )
    col = extract_fields(lines, "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0

    # Phone and PIN should be in other fields, not MRP
    care = col.best("consumer_care_contact")
    assert care is not None


def test_evidence_extractor_no_mrp_returns_none():
    """Evidence-aware extractor: no MRP label -> no MRP field."""
    lines = _lines(
        "Manufacturer: ABC Foods",
        "Hyderabad - 500032",
        "Customer Care: 1800-123-4567",
        "Date of Mfg: 04/09/2026",
        "Net Quantity: 500 g",
    )
    col = extract_fields(lines, "img")
    assert col.best("mrp") is None


def test_evidence_extractor_mrp_rupee_recovery():
    """Evidence-aware: ₹ misread as 7 -> recovers correct MRP."""
    lines = _lines("MRP: 7650")
    col = extract_fields(lines, "img")
    mrp = col.best("mrp")
    assert mrp is not None
    assert mrp.numeric == 650.0


# ======================================================================
# Compliance engine receives NOT_DETECTED when MRP is genuinely absent
# ======================================================================

def test_compliance_receives_not_detected_for_missing_mrp():
    """When MRP is absent, compliance validators see no MRP field -> FAIL."""
    from app.compliance.rule_engine import run_rules
    from app.compliance.validators import Status

    text = (
        "Premium Tea\n"
        "Net Wt. 500 g\n"
        "Mfd. by ABC Foods Pvt Ltd\n"
        "Customer Care: 1800-123-456\n"
    )
    res = run_extraction(text)
    assert not res.has("mrp")

    checks = run_rules(res, ["3", "6"], "FOOD")
    for check in checks:
        if check.rule_number in ("3", "6"):
            assert check.status in (Status.FAIL, Status.REVIEW)


# ======================================================================
# Edge cases
# ======================================================================

def test_empty_text_no_mrp():
    """Empty text -> no MRP."""
    res = run_extraction("")
    assert not res.has("mrp")

    col = extract_fields([], "img")
    assert col.best("mrp") is None


def test_mrp_with_comma_and_decimal():
    """MRP ₹1,250.00 -> 1250.0"""
    text = "MRP: ₹1,250.00"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 1250.0


def test_mrp_with_inr():
    """MRP INR 650 -> 650.0"""
    text = "MRP INR 650"
    res = run_extraction(text)
    assert res.has("mrp")
    assert res.get("mrp").numeric == 650.0


def test_mrp_variants_all_correct():
    """All recognized MRP declaration formats produce the correct value."""
    cases = [
        ("MRP: ₹650", 650.0),
        ("MRP ₹650", 650.0),
        ("MRP Rs. 650", 650.0),
        ("MRP Rs 650", 650.0),
        ("MRP: Rs. 650/-", 650.0),
        ("M.R.P. ₹650", 650.0),
        ("M.R.P. Rs. 650", 650.0),
        ("Maximum Retail Price: ₹650", 650.0),
        ("Maximum Retail Price Rs. 650", 650.0),
        ("MRP: Rs.650", 650.0),
    ]
    for text, expected in cases:
        res = run_extraction(text)
        assert res.has("mrp"), f"Failed for '{text}'"
        assert res.get("mrp").numeric == expected, f"Wrong value for '{text}': {res.get('mrp').numeric}"


# ======================================================================
# Existing golden dataset tests continue to pass (marker test)
# ======================================================================

def test_golden_dataset_still_passes():
    """Verify the golden dataset fixtures still extract correctly."""
    import json
    from pathlib import Path

    expected_path = (
        Path(__file__).resolve().parent / "fixtures" / "ocr" / "expected" / "fields.json"
    )
    if not expected_path.exists():
        pytest.skip("Golden dataset not found")

    with open(expected_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    field_names = [
        "commodity_name", "net_quantity", "mrp", "manufacturer_name",
        "manufacturer_address", "country_of_origin", "batch_number",
        "packing_date", "best_before_date", "consumer_care_contact",
    ]

    correct = total = 0
    for key, spec in data["fixtures"].items():
        lines = [
            TextLine(text=ln, index=i, y=i * 40)
            for i, ln in enumerate(spec["input_lines"])
        ]
        col = extract_fields(lines, image_id=key)
        for name in field_names:
            exp = spec["expected_fields"].get(name)
            ev = col.best(name)
            act = ev.value if ev else None
            if exp is None:
                continue
            total += 1
            if str(exp).strip().lower() == str(act).strip().lower():
                correct += 1

    assert total > 0
    assert correct / total >= 0.8, f"Golden dataset accuracy too low: {correct}/{total}"
