"""Tests for extraction Phases 7-11: fields, normalizer, confidence, evidence_merger."""

import numpy as np
import pytest

from app.services.extraction import normalizer as norm
from app.services.extraction import confidence as conf
from app.services.extraction.evidence import FieldEvidence, FieldStatus, FieldCollection
from app.services.extraction.fields import extract_fields
from app.services.analysis import evidence_merger
from app.services.ocr.line_builder import TextLine


def _line(text, y=0):
    return TextLine(text=text, index=0, y=y)


# ---------- Phase 8: normalizer ----------

def test_canonical_unit():
    assert norm.canonical_unit("kg") == ("weight", "kg")
    assert norm.canonical_unit("ml") == ("volume", "ml")
    assert norm.canonical_unit("nos.") == ("number", "nos")
    assert norm.canonical_unit("blah") is None


def test_normalize_quantity_kg_to_g():
    kind, unit, num = norm.normalize_quantity(1.0, "kg")
    assert unit == "g" and num == 1000.0


def test_normalize_quantity_l_to_ml():
    kind, unit, num = norm.normalize_quantity(1.5, "l")
    assert unit == "ml" and num == 1500.0


def test_parse_number_formats():
    assert norm.parse_number("Rs. 1,200.50") == 1200.5
    assert norm.parse_number("₹450") == 450.0
    assert norm.parse_number("garbage") is None


def test_is_price_context():
    assert norm.is_price_context("MRP Rs. 450")
    assert not norm.is_price_context("net weight 500 g")


def test_normalize_due_date():
    assert norm.normalize_due_date("08/2026") == "2026-08-00"
    assert norm.normalize_due_date("Jan 2025") == "2025-01-00"
    assert norm.normalize_due_date("not-a-date") == ""


# ---------- Phase 9: confidence ----------

def test_combine_multiplies():
    assert conf.combine(0.9, 0.9) == pytest.approx(0.81, abs=1e-3)
    assert conf.combine(None) >= 0.0


def test_field_status():
    assert conf.field_status(0.9, True) == FieldStatus.DETECTED
    assert conf.field_status(0.9, False) == FieldStatus.MISSING
    assert conf.field_status(0.2, True) == FieldStatus.UNCERTAIN


# ---------- Phase 7: fields (evidence-aware) ----------

def test_extract_fields_mrp_and_net_qty():
    lines = [
        _line("MRP Rs. 450", y=0),
        _line("Net Wt. 500 g", y=40),
    ]
    col = extract_fields(lines, image_id="img-1")
    mrp = col.best("mrp")
    assert mrp is not None and mrp.value == "450" and mrp.image_id == "img-1"
    nq = col.best("net_quantity")
    assert nq is not None and nq.numeric == 500.0 and nq.unit == "g"


def test_extract_fields_commmodity_typo_tolerant():
    lines = [_line("Commedity Name: Biscuit")]  # OCR typo
    col = extract_fields(lines, image_id="i")
    c = col.best("commodity_name")
    assert c is not None and "Biscuit" in c.value


def test_extract_fields_batch_and_country():
    lines = [
        _line("Batch No: BN-2601", y=0),
        _line("Country of Origin: India", y=40),
    ]
    col = extract_fields(lines, image_id="i")
    assert col.best("batch_number").value == "BN-2601"
    assert col.best("country_of_origin").value == "India"


def test_extract_fields_unsure_net_quantity_label_only():
    lines = [_line("Net Wt.")]  # label present, value absent
    col = extract_fields(lines, image_id="i")
    ev = col.best("net_quantity")
    assert ev is not None and ev.status == FieldStatus.UNCERTAIN


# ---------- Phase 10/11: evidence_merger ----------

def _ev(field, value, conf_n, image_id):
    return FieldEvidence(
        field_name=field, value=value, image_id=image_id,
        confidence=conf_n, numeric=float(value) if isinstance(value, (int, float)) else None,
    )


def test_merge_combines_images():
    c1 = FieldCollection(image_id="front")
    c1.add(_ev("mrp", "450", 0.9, "front"))
    c2 = FieldCollection(image_id="back")
    c2.add(_ev("mrp", "480", 0.8, "back"))
    merged = evidence_merger.merge_collections([c1, c2])
    assert len(merged["mrp"]) == 2


def test_conflict_detection_on_different_scalars():
    c1 = FieldCollection(image_id="front")
    c1.add(_ev("mrp", "450", 0.9, "front"))
    c2 = FieldCollection(image_id="back")
    c2.add(_ev("mrp", "480", 0.8, "back"))
    merged = evidence_merger.merge_collections([c1, c2])
    resolved = evidence_merger.resolve_conflicts(merged)
    assert resolved["mrp"]["status"] == "CONFLICTING"
    assert len(resolved["mrp"]["candidates"]) == 2


def test_consistent_values_not_conflicting():
    c1 = FieldCollection(image_id="front")
    c1.add(_ev("mrp", "450", 0.9, "front"))
    c2 = FieldCollection(image_id="back")
    c2.add(_ev("mrp", "450", 0.8, "back"))
    resolved = evidence_merger.resolve_conflicts(
        evidence_merger.merge_collections([c1, c2])
    )
    assert resolved["mrp"]["status"] == "DETECTED"


def test_uncertain_becomes_uncertain():
    c = FieldCollection(image_id="i")
    c.add(FieldEvidence("net_quantity", value=None, image_id="i", confidence=0.3,
                        status=FieldStatus.UNCERTAIN))
    merged = evidence_merger.merge_collections([c])
    resolved = evidence_merger.resolve_conflicts(merged)
    assert resolved["net_quantity"]["status"] == "UNCERTAIN"


# ---------- Phase 15: golden dataset ----------

def test_golden_dataset_extraction_accuracy():
    """Run the deterministic extractors over the golden dataset and assert
    strong accuracy (Phase 15 evaluation harness)."""
    import json
    from pathlib import Path
    from app.services.ocr.line_builder import TextLine
    from app.services.extraction.fields import extract_fields

    expected_path = (
        Path(__file__).resolve().parent / "fixtures" / "ocr" / "expected" / "fields.json"
    )
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
                continue  # not required
            total += 1
            if str(exp).strip().lower() == str(act).strip().lower():
                correct += 1

    assert total > 0
    assert correct / total >= 0.8, f"extraction accuracy too low: {correct}/{total}"