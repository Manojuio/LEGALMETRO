"""Applicability and exemption engine.

Determines WHICH rules apply to a given product/analysis, before validation.

Flow:
1. Start from the product's category-derived applicable rule list (or a default)
2. Remove rules flagged NOT_APPLICABLE (e.g. imported-only rule on domestic goods)
3. Apply exemptions that match the product context
4. Return the final applicable rule set

This is the "brain before validation" — selecting the right rules is as
important as checking them.
"""

from dataclasses import dataclass, field

import json
from pathlib import Path


@dataclass
class ApplicabilityResult:
    applicable_rules: list[str]
    exemptions_applied: list[str] = field(default_factory=list)
    note: str = ""


def _load_exemptions() -> list:
    path = Path(__file__).resolve().parent.parent.parent / "rules" / "exemptions.json"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["exemptions"]


def _load_exemptions_cached():
    if not hasattr(_load_exemptions_cached, "_cache"):
        _load_exemptions_cached._cache = _load_exemptions()
    return _load_exemptions_cached._cache


def evaluate_exemption(rule_num: str, context: dict) -> bool:
    """Return True if the given rule is exempt for this context.

    context is a dict of product/analysis attributes (is_exported,
    sale_type, surface_area, package_type, category, etc). If a context key
    used by an exemption is absent, we do NOT apply the exemption (fail-safe:
    rules stay applicable).
    """
    exemptions = _load_exemptions_cached()
    for ex in exemptions:
        if rule_num in ex.get("affected_rules", []):
            condition = ex.get("condition", "")
            if _match_condition(condition, context):
                return True
    return False


def _match_condition(condition: str, context: dict) -> bool:
    """Evaluate a simple 'key op value' condition string against context.

    Supports == true/false to a key, and < / > on numeric keys.
    Unknown keys -> condition fails (no exemption).
    """
    condition = condition.strip()
    # == boolean or string
    if "==" in condition:
        left, right = condition.split("==", 1)
        key = left.strip()
        val = right.strip().strip('"\'')
        actual = context.get(key)
        if val.lower() == "true":
            return actual is True or actual in (True, "true", "True", "1")
        if val.lower() == "false":
            return actual in (False, "false", "False", "0", None)
        return str(actual) == val
    # numeric comparisons
    for op in ("<", ">"):
        if op in condition:
            left, right = condition.split(op, 1)
            key = left.strip()
            try:
                limit = float(right.strip())
            except ValueError:
                return False
            actual = context.get(key)
            if actual is None:
                return False
            try:
                actual_f = float(actual)
            except (TypeError, ValueError):
                return False
            return actual_f < limit if op == "<" else actual_f > limit
    return False


def determine_applicability(
    candidate_rules: list[str],
    context: dict,
) -> ApplicabilityResult:
    """Filter candidate rules to the applicable set.

    Removes rules that are 'NOT_APPLICABLE' because their preconditions are
    unmet (e.g. imported-only rule on a domestic product), then removes rules
    covered by an exemption.
    """
    applicable = []
    exemptions_applied = []
    for rule_num in candidate_rules:
        # Imported-only rule (16) — only applies to imports
        if rule_num == "16":
            if not context.get("is_imported"):
                continue
        # Rule 19/20 (physical) — always applicable in the sense they must be
        # flagged, but handled as NOT_APPLICABLE for image-only scanning.

        if evaluate_exemption(rule_num, context):
            exemptions_applied.append(rule_num)
            continue
        applicable.append(rule_num)

    return ApplicabilityResult(
        applicable_rules=applicable,
        exemptions_applied=exemptions_applied,
        note="Applicability computed from category + exemptions",
    )
