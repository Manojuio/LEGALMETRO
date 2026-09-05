"""Product classification: identify the product category/subcategory.

Currently keyword-based using the category dictionary in rules/categories.json.
OCR text + extracted commodity name are matched against category keywords.

Classification is deterministic and gives a confidence. It does NOT decide
compliance — it selects which rules are applicable.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClassificationResult:
    category: str
    subcategory: str
    name: str
    confidence: float
    applicable_rules: list[str]


def _load_categories() -> list:
    path = Path(__file__).resolve().parent.parent.parent / "rules" / "categories.json"
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["categories"]


def _load_categories_cached():
    if not hasattr(_load_categories_cached, "_cache"):
        _load_categories_cached._cache = _load_categories()
    return _load_categories_cached._cache


def classify(
    commodity_name: str | None,
    raw_text: str = "",
    existing_category: str | None = None,
) -> ClassificationResult:
    """Classify a product into a category/subcategory by keyword matching.

    Scores each subcategory by how many of its keywords appear in the combined
    text (commodity name given more weight). Returns the best match.

    If *existing_category* is provided (the inspector's manual selection), it
    takes priority: we look up that category's rules and subcategories and
    return them immediately without keyword guessing.  This prevents the
    automatic classifier from overwriting an explicit inspector choice with
    "FOOD" when OCR keywords are sparse.
    """
    categories = _load_categories_cached()

    # --- Inspector-selected category takes priority ---
    if existing_category:
        norm = existing_category.strip().upper()
        for cat in categories:
            if cat["id"].upper() == norm:
                # Use the first (default) subcategory for this category
                default_sub = cat["subcategories"][0] if cat["subcategories"] else None
                if default_sub:
                    return ClassificationResult(
                        category=cat["id"],
                        subcategory=default_sub["id"],
                        name=commodity_name or default_sub.get("name", cat["id"]),
                        confidence=0.95,
                        applicable_rules=list(default_sub.get("applicable_rules", [])),
                    )
                # Category found but no subcategories — still honour the choice
                return ClassificationResult(
                    category=cat["id"],
                    subcategory="GENERAL",
                    name=commodity_name or cat["id"],
                    confidence=0.9,
                    applicable_rules=["3", "4", "5", "6", "7", "8", "9", "10",
                                       "11", "12", "13", "14", "15"],
                )

    # --- Keyword-based auto-classification (unchanged) ---
    combined = f"{commodity_name or ''} {raw_text}".lower()

    best = None
    best_score = 0
    for cat in categories:
        for sub in cat["subcategories"]:
            keywords = sub.get("keywords", [])
            score = 0
            for kw in keywords:
                if kw in combined:
                    weight = 2 if commodity_name and kw in commodity_name.lower() else 1
                    score += weight
            if score > best_score:
                best_score = score
                best = (cat, sub)

    if best is None or best_score == 0:
        # No keyword match and no inspector selection — use the first
        # available category rather than hard-coding FOOD.
        fallback_cat = categories[0] if categories else None
        if fallback_cat:
            fallback_sub = fallback_cat["subcategories"][0] if fallback_cat["subcategories"] else None
            return ClassificationResult(
                category=fallback_cat["id"],
                subcategory=fallback_sub["id"] if fallback_sub else "GENERAL",
                name=commodity_name or "Unknown Product",
                confidence=0.1,
                applicable_rules=list(
                    fallback_sub.get("applicable_rules", [])
                    if fallback_sub
                    else ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]
                ),
            )
        # Absolute fallback (categories.json missing or empty)
        return ClassificationResult(
            category="OTHER",
            subcategory="GENERAL",
            name=commodity_name or "Unknown Product",
            confidence=0.1,
            applicable_rules=["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
        )

    cat, sub = best
    confidence = min(0.95, 0.5 + best_score * 0.1)
    return ClassificationResult(
        category=cat["id"],
        subcategory=sub["id"],
        name=commodity_name or sub["name"],
        confidence=round(confidence, 2),
        applicable_rules=list(sub.get("applicable_rules", [])),
    )
