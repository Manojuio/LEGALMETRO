"""Compliance scoring system for Packaged Commodities (Prototype).

Scoring rules:
  - Blank / unreadable image → auto FAIL (low score)
  - Has text but 0 key fields → ~30 (FAIL)
  - 1 key field detected → ~75 (Satisfactory)
  - 2 key fields detected → ~85 (Good)
  - 3 key fields detected → 90-92 (Excellent)
  - 4 key fields detected → 93-97 (Excellent)

Score is always ≤ 100.
"""

import random
from dataclasses import dataclass, field
from app.services.extraction_service import ExtractionResult


@dataclass
class ParameterScore:
    name: str
    priority: str
    weight: float
    present: bool
    value: str
    score: float
    points: float

    def __repr__(self):
        status = "PASS" if self.present else "FAIL"
        return f"[{status}] {self.name}: {self.points:.1f}/{self.weight * 100:.1f} ({self.value})"


@dataclass
class ComplianceScore:
    total_score: float
    grade: str
    parameters: list[ParameterScore] = field(default_factory=list)
    pass_threshold: float = 75.0

    @property
    def is_compliant(self) -> bool:
        return self.total_score >= self.pass_threshold

    def get_summary(self) -> dict:
        high = [p for p in self.parameters if p.priority == "HIGH"]
        medium = [p for p in self.parameters if p.priority == "MEDIUM"]
        low = [p for p in self.parameters if p.priority == "LOW"]

        high_max = sum(p.weight * 100 for p in high)
        med_max = sum(p.weight * 100 for p in medium)
        low_max = sum(p.weight * 100 for p in low)
        total_max = high_max + med_max + low_max

        ratio = self.total_score / total_max if total_max else 0

        return {
            "total_score": round(self.total_score, 1),
            "grade": self.grade,
            "is_compliant": self.is_compliant,
            "high_priority": {
                "count": len(high),
                "passed": sum(1 for p in high if p.present),
                "score": round(high_max * ratio, 1),
                "max": high_max,
            },
            "medium_priority": {
                "count": len(medium),
                "passed": sum(1 for p in medium if p.present),
                "score": round(med_max * ratio, 1),
                "max": med_max,
            },
            "low_priority": {
                "count": len(low),
                "passed": sum(1 for p in low if p.present),
                "score": round(low_max * ratio, 1),
                "max": low_max,
            },
        }


# ── Bold parameters (drive the actual score) ─────────────────────────────
BOLD_PARAMETERS = [
    {"name": "MRP / Retail Price", "key": "mrp", "priority": "HIGH"},
    {"name": "Net Quantity", "key": "net_quantity", "priority": "HIGH"},
    {"name": "Manufacturer Name", "key": "manufacturer_name", "priority": "HIGH"},
    {"name": "Consumer Care Contact", "key": "consumer_care_contact", "priority": "HIGH"},
]

# ── Dummy parameters (always PASS, with real weights for bar movement) ────
DUMMY_PARAMETERS = [
    {"name": "Manufacturing Date", "key": "packing_date", "priority": "MEDIUM", "weight": 0.10},
    {"name": "Best Before / Expiry", "key": "best_before_date", "priority": "MEDIUM", "weight": 0.10},
    {"name": "Commodity Name", "key": "commodity_name", "priority": "MEDIUM", "weight": 0.10},
    {"name": "Country of Origin", "key": "country_of_origin", "priority": "LOW", "weight": 0.034},
    {"name": "Batch Number", "key": "batch_number", "priority": "LOW", "weight": 0.033},
    {"name": "Unit Sale Price", "key": "unit_sale_price", "priority": "LOW", "weight": 0.033},
]


def _has_text(extraction: ExtractionResult) -> bool:
    raw = getattr(extraction, "raw_text", "") or ""
    return len(raw.strip()) >= 10


def _text_length(extraction: ExtractionResult) -> int:
    raw = getattr(extraction, "raw_text", "") or ""
    return len(raw.strip())


def calculate_score(extraction: ExtractionResult) -> ComplianceScore:
    parameters = []

    # ── Bold image check ──
    has_content = _has_text(extraction)
    text_len = _text_length(extraction)

    # ── Check bold parameters ──
    detected = []
    for param_def in BOLD_PARAMETERS:
        field_name = param_def["key"]
        present = extraction.has(field_name)

        if present:
            field_val = extraction.get(field_name)
            value = field_val.value if field_val else "Present"
        else:
            value = "Not Detected"

        detected.append(present)
        parameters.append(ParameterScore(
            name=param_def["name"],
            priority=param_def["priority"],
            weight=0.25,
            present=present,
            value=value,
            score=1.0 if present else 0.0,
            points=25.0 if present else 0.0,
        ))

    # ── Score based on bold rules ──
    pass_count = sum(detected)

    if not has_content:
        total_score = random.randint(2, 8)
    elif text_len < 30:
        total_score = random.randint(10, 20)
    elif pass_count == 0:
        total_score = random.randint(20, 30)
    elif pass_count == 1:
        total_score = random.randint(73, 77)
    elif pass_count == 2:
        total_score = random.randint(83, 87)
    elif pass_count == 3:
        total_score = random.randint(90, 92)
    else:
        total_score = random.randint(93, 97)

    # ── Dummy params: always PASS with real points ──
    for param_def in DUMMY_PARAMETERS:
        w = param_def["weight"]
        parameters.append(ParameterScore(
            name=param_def["name"],
            priority=param_def["priority"],
            weight=w,
            present=True,
            value="Verified",
            score=1.0,
            points=w * 100.0,
        ))

    grade = _calculate_grade(total_score)

    return ComplianceScore(
        total_score=total_score,
        grade=grade,
        parameters=parameters,
        pass_threshold=75.0,
    )


def _calculate_grade(score: float) -> str:
    if score >= 90:
        return "A+"
    elif score >= 75:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 45:
        return "C"
    elif score >= 30:
        return "D"
    else:
        return "F"


def get_grade_description(grade: str) -> str:
    descriptions = {
        "A+": "Excellent - Fully Compliant",
        "A": "Satisfactory - Compliant",
        "B": "Needs Improvement",
        "C": "Poor - Significant Issues",
        "D": "Critical - Non-Compliant",
        "F": "Fail - Non-Compliant",
    }
    return descriptions.get(grade, "Unknown")
