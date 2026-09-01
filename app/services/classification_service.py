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


def classify(commodity_name: str | None, raw_text: str = "") -> ClassificationResult:
    """Classify a product into a category/subcategory by keyword matching.

    Scores each subcategory by how many of its keywords appear in the combined
    text (commodity name given more weight). Returns the best match.
    """
    categories = _load_categories_cached()
    combined = f"{commodity_name or ''} {raw_text}".lower()

    best = None
    best_score = 0
    for cat in categories:
        for sub in cat["subcategories"]:
            keywords = sub.get("keywords", [])
            score = 0
            for kw in keywords:
                if kw in combined:
                    # keywords in the commodity name count more
                    weight = 2 if commodity_name and kw in commodity_name.lower() else 1
                    score += weight
            if score > best_score:
                best_score = score
                best = (cat, sub)

    if best is None or best_score == 0:
        # Fall back to a generic food category so the scan still runs
        return ClassificationResult(
            category="FOOD",
            subcategory="FOOD_GENERAL",
            name=commodity_name or "Unknown Product",
            confidence=0.1,
            applicable_rules=["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
        )

    cat, sub = best
    # Scale confidence: many strong matches -> high confidence
    confidence = min(0.95, 0.5 + best_score * 0.1)
    return ClassificationResult(
        category=cat["id"],
        subcategory=sub["id"],
        name=commodity_name or sub["name"],
        confidence=round(confidence, 2),
        applicable_rules=list(sub.get("applicable_rules", [])),
    )
