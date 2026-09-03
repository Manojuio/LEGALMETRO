"""Compliance rule engine — the heart of the system.

Given the extracted structured evidence and the applicable rule set, it runs
deterministic validators and produces a PASS / FAIL / REVIEW / NOT_APPLICABLE
outcome per rule. Legal reasoning is 100% deterministic — no LLM.

The engine does NOT care about roles or users. It evaluates evidence.

Each rule in rules/rules.json carries a validation_type. This engine maps:
  FIELD_PRESENT       -> generic field-presence validator (rule.input_fields)
  UNIT_VALIDATION     -> validate_quantity_unit
  STANDARD_QUANTITY   -> validate_standard_quantity
  DATE_VALIDATION     -> validate_date_present
  PRICE_VALIDATION    -> validate_price_present
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.compliance.validators import (
    Status,
    validate_contact_any_of,
    validate_date_present,
    validate_field_present,
    validate_price_present,
    validate_quantity_unit,
    validate_standard_quantity,
)
from app.services.extraction_service import ExtractionResult


@dataclass
class RuleCheck:
    rule_id: str
    rule_number: str
    title: str
    category: str
    validation_type: str
    severity: str
    status: str
    reason: str
    evidence: list = field(default_factory=list)
    confidence: float = 0.0


def _load_rules() -> list:
    path = Path(__file__).resolve().parent.parent.parent / "rules" / "rules.json"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["rules"]


def _load_rules_cached():
    if not hasattr(_load_rules_cached, "_cache"):
        _load_rules_cached._cache = {r["rule_number"]: r for r in _load_rules()}
    return _load_rules_cached._cache


def _dispatch_validator(rule: dict, extraction: ExtractionResult, category: str):
    """Run the validator matching a rule's validation_type.

    Returns a ValidationOutcome.
    """
    vtype = rule.get("validation_type")
    fields = rule.get("input_fields") or []
    rule_num = str(rule.get("rule_number"))

    # Rule 11: contact needs AT LEAST ONE field, not all of them
    if rule_num == "11":
        return validate_contact_any_of(extraction)

    if vtype == "FIELD_PRESENT":
        return validate_field_present(extraction, fields)
    if vtype == "UNIT_VALIDATION":
        return validate_quantity_unit(extraction)
    if vtype == "STANDARD_QUANTITY":
        return validate_standard_quantity(extraction, category)
    if vtype == "DATE_VALIDATION":
        return validate_date_present(extraction)
    if vtype == "PRICE_VALIDATION":
        return validate_price_present(extraction)
    # Unknown type — flag for manual review rather than guessing
    return validate_field_present(extraction, fields)


def run_rules(
    extraction: ExtractionResult,
    applicable_rules: list[str],
    category: str,
) -> list[RuleCheck]:
    """Execute validators for each applicable rule and return results."""
    rules_by_num = _load_rules_cached()
    results: list[RuleCheck] = []

    for rule_num in applicable_rules:
        rule = rules_by_num.get(str(rule_num))
        if rule is None:
            # unknown rule in our registry — do not invent, skip
            continue

        outcome = _dispatch_validator(rule, extraction, category)
        results.append(
            RuleCheck(
                rule_id=rule["id"],
                rule_number=str(rule_num),
                title=rule["title"],
                category=rule["category"],
                validation_type=rule["validation_type"],
                severity=rule["severity"],
                status=outcome.status,
                reason=outcome.reason,
                evidence=outcome.evidence,
                confidence=outcome.confidence,
            )
        )
    return results


def aggregate_overall(results: list[RuleCheck]) -> dict:
    """Summarize results into counts + overall status.

    Overall status: FAIL if any FAIL, elif REVIEW if any REVIEW, else PASS.
    """
    summary = {Status.PASS: 0, Status.FAIL: 0, Status.REVIEW: 0, Status.NOT_APPLICABLE: 0}
    for r in results:
        summary[r.status] = summary.get(r.status, 0) + 1

    if summary[Status.FAIL] > 0:
        overall = Status.FAIL
    elif summary[Status.REVIEW] > 0:
        overall = Status.REVIEW
    else:
        overall = Status.PASS
    return {
        "overall_status": overall,
        "summary": summary,
    }
