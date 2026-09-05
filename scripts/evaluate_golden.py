"""Golden dataset evaluation — ``scripts/evaluate_golden.py`` (Phase 15).

Runs the deterministic **field-extraction** layer over the known ground-truth
label text and reports per-fixture, per-field accuracy. This is honest: OCR is
non-deterministic and measured separately on real photos; here we verify the
deterministic extractors do not regress against known-good labels.

Usage:
    python -m scripts.evaluate_golden
"""

import json
import sys
from pathlib import Path

from app.services.ocr.line_builder import TextLine
from app.services.extraction.fields import extract_fields

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PATH = ROOT / "tests" / "fixtures" / "ocr" / "expected" / "fields.json"


def _lines(text_lines: list[str]):
    return [
        TextLine(text=ln, index=i, y=i * 40) for i, ln in enumerate(text_lines)
    ]


def _fields_to_map(field_names: list[str], col):
    """Return {field_name: extracted_value} using best evidence."""
    out = {}
    for name in field_names:
        ev = col.best(name)
        out[name] = ev.value if ev else None
    return out


def evaluate() -> dict:
    with open(EXPECTED_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    field_names = [
        "commodity_name", "net_quantity", "mrp", "manufacturer_name",
        "manufacturer_address", "country_of_origin", "batch_number",
        "packing_date", "best_before_date", "consumer_care_contact",
    ]

    report = {"fixtures": [], "total_correct": 0, "total_expected": 0}

    for key, spec in data["fixtures"].items():
        col = extract_fields(_lines(spec["input_lines"]), image_id=key)
        got = _fields_to_map(field_names, col)
        expected = spec["expected_fields"]

        per_fixture = {"fixture": key, "fields": {}, "correct": 0, "count": 0}
        for name in field_names:
            exp = expected.get(name)
            act = got.get(name)
            # null expected = we don't require it (may be absent)
            ok = (exp is None) or (exp == act) or _lenient_equal(exp, act)
            per_fixture["fields"][name] = {"expected": exp, "actual": act, "ok": ok}
            if exp is not None:
                report["total_expected"] += 1
                if ok:
                    report["total_correct"] += 1
                    per_fixture["correct"] += 1
                per_fixture["count"] += 1
        per_fixture["accuracy"] = (
            round(per_fixture["correct"] / per_fixture["count"], 3)
            if per_fixture["count"] else 0.0
        )
        report["fixtures"].append(per_fixture)

    report["accuracy"] = (
        round(report["total_correct"] / report["total_expected"], 3)
        if report["total_expected"] else 0.0
    )
    return report


def _lenient_equal(exp, act):
    """Case-insensitive, whitespace-folded comparison."""
    if exp is None or act is None:
        return False
    return str(exp).strip().lower() == str(act).strip().lower()


def main():
    report = evaluate()
    print(json.dumps(report, indent=2))
    print(f"\nOverall extraction accuracy: {report['accuracy']:.1%}")
    return 0 if report["accuracy"] >= 0.5 else 1


if __name__ == "__main__":
    sys.exit(main())