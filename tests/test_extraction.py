"""Unit tests for information extraction and rule-engine decision integrity.

These verify that extraction is deterministic and that the engine:
- never invents data (missing fields -> FAIL or REVIEW, never PASS)
- returns REVIEW instead of FAIL when OCR is unreliable
"""

from app.compliance.rule_engine import aggregate_overall, run_rules
from app.compliance.validators import Status
from app.services import extraction_service


def _sample_label() -> str:
    return """Premium Tea
Net Wt. 500 g
MRP Rs. 450
Mfd. by ABC Foods Pvt Ltd
Plot 12, Industrial Area, Delhi
Made in India
Batch No: BN-2601
Packed: 08/2026
Best Before: 24 months
Customer Care: 1800-123-456
"""


def test_full_extraction_sample_label():
    res = extraction_service.run_extraction(_sample_label())
    assert res.get("net_quantity").numeric == 500.0
    assert res.get("net_quantity").unit == "g"
    assert res.get("mrp").numeric == 450.0
    assert "ABC Foods" in res.get("manufacturer_name").value
    assert "Delhi" in res.get("manufacturer_address").value
    assert res.get("country_of_origin").value == "India"
    assert res.get("batch_number").value == "BN-2601"
    assert res.get("consumer_care_contact").value
    assert res.get("commodity_name").value == "Premium Tea"


def test_missing_fields_not_invented():
    res = extraction_service.run_extraction("no declarations here at all")
    assert not res.has("mrp")
    assert not res.has("net_quantity")
    assert not res.has("manufacturer_name")


def test_net_weight_label_without_unit_is_review():
    """OCR saw 'NET WEIGHT' but not the value/unit -> honest REVIEW not FAIL."""
    res = extraction_service.run_extraction("NET WEIGHT\nsome unreadable pixels")
    nq = res.get("net_quantity")
    assert nq is not None
    assert nq.unit is None  # partial field, marked unreliable

    # Rule 12 (UNIT_VALIDATION) should be REVIEW, not FAIL
    checks = run_rules(res, ["12"], "FOOD")
    assert checks[0].status == Status.REVIEW

    # Rule 13 standard quantity also REVIEW when unit unknown
    checks13 = run_rules(res, ["13"], "FOOD")
    assert checks13[0].status == Status.REVIEW


def test_best_before_duration_counts_as_date():
    res = extraction_service.run_extraction("BEST BEFORE 9 MONTHS FROM PACKAGING")
    assert res.has("best_before_date")
    bb = res.get("best_before_date")
    assert "9 MONTHS" in bb.value


def test_commodity_label_with_ocr_typo():
    res = extraction_service.run_extraction(
        "Commedity Name: Creme Delight (Orange Flavoured Creme Biscuits)"
    )
    assert res.get("commodity_name") is not None
    assert "Creme Delight" in res.get("commodity_name").value


def test_country_of_origin_product_of():
    res = extraction_service.run_extraction("Product of India")
    assert res.get("country_of_origin").value == "India"


def test_compliance_rules_never_pass_on_empty_evidence():
    empty = extraction_service.run_extraction("")
    checks = run_rules(empty, ["3", "4", "5", "6", "10", "11", "12", "14", "15"], "FOOD")
    for check in checks:
        assert check.status in (Status.FAIL, Status.REVIEW, Status.NOT_APPLICABLE)
        assert check.status != Status.PASS


def test_aggregate_overall_priority():
    class _C:
        status = Status.REVIEW
    assert aggregate_overall([_C()])["overall_status"] == Status.REVIEW

    class _F:
        status = Status.FAIL
    assert aggregate_overall([_C(), _F()])["overall_status"] == Status.FAIL

    class _P:
        status = Status.PASS
    assert aggregate_overall([_P()])["overall_status"] == Status.PASS