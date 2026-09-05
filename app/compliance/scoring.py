"""Compliance scoring — derived from real rule engine results.

Score = weighted sum of rule outcomes:
  PASS            → full weight toward 100
  REVIEW          → 50 % of weight
  FAIL            → 0
  NOT_APPLICABLE  → excluded from denominator

Priority weights (2 levels):
  ESSENTIAL  = 10 pts  (core declarations every product must have)
  SUPPORTING =  5 pts  (additional requirements)
"""

from dataclasses import dataclass, field


SEVERITY_WEIGHTS = {"HIGH": 10, "MEDIUM": 5}

# Display mapping: rule severity → human-readable priority label
PRIORITY_LABELS = {"HIGH": "ESSENTIAL", "MEDIUM": "SUPPORTING"}


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
        return f"[{status}] {self.name}: {self.points:.1f}/{self.weight:.1f} ({self.value})"


@dataclass
class ComplianceScore:
    total_score: float
    grade: str
    parameters: list[ParameterScore] = field(default_factory=list)
    pass_threshold: float = 50.0

    @property
    def is_compliant(self) -> bool:
        return self.total_score >= self.pass_threshold

    def get_summary(self) -> dict:
        essential = [p for p in self.parameters if p.priority == "ESSENTIAL"]
        supporting = [p for p in self.parameters if p.priority == "SUPPORTING"]

        ess_max = sum(p.weight for p in essential)
        ess_pts = sum(p.points for p in essential)
        sup_max = sum(p.weight for p in supporting)
        sup_pts = sum(p.points for p in supporting)

        return {
            "total_score": round(self.total_score, 1),
            "grade": self.grade,
            "is_compliant": self.is_compliant,
            "pass_threshold": self.pass_threshold,
            "essential": {
                "count": len(essential),
                "passed": sum(1 for p in essential if p.present),
                "score": round(ess_pts, 1),
                "max": ess_max,
                "percentage": round((ess_pts / ess_max * 100) if ess_max else 0, 1),
            },
            "supporting": {
                "count": len(supporting),
                "passed": sum(1 for p in supporting if p.present),
                "score": round(sup_pts, 1),
                "max": sup_max,
                "percentage": round((sup_pts / sup_max * 100) if sup_max else 0, 1),
            },
        }


def calculate_score(rule_checks: list, extraction=None) -> ComplianceScore:
    """Calculate score from real rule engine results.

    Parameters
    ----------
    rule_checks : list[RuleCheck]
        Output of rule_engine.run_rules().
    extraction : ExtractionResult, optional
        Used only to check if OCR produced any text at all.
    """
    parameters: list[ParameterScore] = []
    total_weight = 0.0
    earned = 0.0

    for rc in rule_checks:
        weight = SEVERITY_WEIGHTS.get(rc.severity, 5)
        priority = PRIORITY_LABELS.get(rc.severity, "SUPPORTING")

        if rc.status == "NOT_APPLICABLE":
            parameters.append(ParameterScore(
                name=f"Rule {rc.rule_number}: {rc.title}",
                priority=priority,
                weight=weight,
                present=False,
                value="N/A",
                score=0.0,
                points=0.0,
            ))
            continue

        total_weight += weight

        if rc.status == "PASS":
            pts = weight
        elif rc.status == "REVIEW":
            pts = weight * 0.5
        else:
            # FAIL
            pts = 0.0

        earned += pts
        parameters.append(ParameterScore(
            name=f"Rule {rc.rule_number}: {rc.title}",
            priority=priority,
            weight=weight,
            present=(rc.status == "PASS"),
            value=rc.status,
            score=1.0 if rc.status == "PASS" else 0.5 if rc.status == "REVIEW" else 0.0,
            points=pts,
        ))

    # Edge case: no applicable rules at all
    if total_weight == 0:
        total_score = 0.0
    else:
        total_score = (earned / total_weight) * 100.0

    # Clamp 0-100
    total_score = max(0.0, min(100.0, total_score))

    grade = _calculate_grade(total_score)

    return ComplianceScore(
        total_score=round(total_score, 1),
        grade=grade,
        parameters=parameters,
        pass_threshold=50.0,
    )


def _calculate_grade(score: float) -> str:
    if score >= 90:
        return "A+"
    elif score >= 75:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 30:
        return "D"
    else:
        return "F"


def get_grade_description(grade: str) -> str:
    descriptions = {
        "A+": "Excellent - Fully Compliant",
        "A": "Very Good - Compliant",
        "B": "Good - Compliant",
        "C": "Satisfactory - Meets Minimum (Compliant)",
        "D": "Poor - Review Required (Non-Compliant)",
        "F": "Fail - Non-Compliant",
    }
    return descriptions.get(grade, "Unknown")
