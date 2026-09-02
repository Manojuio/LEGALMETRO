"""Compliance scoring system for Packaged Commodities.

Selects 10 key parameters based on Legal Metrology guidelines with priority levels:
- HIGH (4 parameters): Weight 15% each = 60% total
- MEDIUM (3 parameters): Weight 10% each = 30% total  
- LOW (3 parameters): Weight ~3.3% each = 10% total

Total possible score: 100 points
"""

from dataclasses import dataclass, field
from app.services.extraction_service import ExtractionResult


@dataclass
class ParameterScore:
    name: str
    priority: str  # HIGH, MEDIUM, LOW
    weight: float
    present: bool
    value: str
    score: float  # 0.0 to 1.0
    points: float  # weight * score
    
    def __repr__(self):
        status = "PASS" if self.present else "FAIL"
        return f"[{status}] {self.name}: {self.points:.1f}/{self.weight * 100:.1f} ({self.value})"


@dataclass 
class ComplianceScore:
    total_score: float  # 0-100
    grade: str  # A+, A, B, C, D, F
    parameters: list[ParameterScore] = field(default_factory=list)
    pass_threshold: float = 80.0
    
    @property
    def is_compliant(self) -> bool:
        return self.total_score >= self.pass_threshold
    
    def get_summary(self) -> dict:
        high = [p for p in self.parameters if p.priority == "HIGH"]
        medium = [p for p in self.parameters if p.priority == "MEDIUM"]
        low = [p for p in self.parameters if p.priority == "LOW"]
        
        return {
            "total_score": round(self.total_score, 1),
            "grade": self.grade,
            "is_compliant": self.is_compliant,
            "high_priority": {
                "count": len(high),
                "passed": sum(1 for p in high if p.present),
                "score": sum(p.points for p in high),
                "max": sum(p.weight * 100 for p in high),
            },
            "medium_priority": {
                "count": len(medium),
                "passed": sum(1 for p in medium if p.present),
                "score": sum(p.points for p in medium),
                "max": sum(p.weight * 100 for p in medium),
            },
            "low_priority": {
                "count": len(low),
                "passed": sum(1 for p in low if p.present),
                "score": sum(p.points for p in low),
                "max": sum(p.weight * 100 for p in low),
            },
        }


# 10 Key Parameters with Weights
PARAMETERS = [
    # HIGH PRIORITY (4 params) - Total 60%
    {"name": "MRP / Retail Price", "key": "mrp", "priority": "HIGH", "weight": 0.15},
    {"name": "Net Quantity", "key": "net_quantity", "priority": "HIGH", "weight": 0.15},
    {"name": "Manufacturer Name", "key": "manufacturer_name", "priority": "HIGH", "weight": 0.15},
    {"name": "Consumer Care Contact", "key": "consumer_care_contact", "priority": "HIGH", "weight": 0.15},
    
    # MEDIUM PRIORITY (3 params) - Total 30%
    {"name": "Manufacturing Date", "key": "packing_date", "priority": "MEDIUM", "weight": 0.10},
    {"name": "Best Before / Expiry", "key": "best_before_date", "priority": "MEDIUM", "weight": 0.10},
    {"name": "Commodity Name", "key": "commodity_name", "priority": "MEDIUM", "weight": 0.10},
    
    # LOW PRIORITY (3 params) - Total 10%
    {"name": "Country of Origin", "key": "country_of_origin", "priority": "LOW", "weight": 0.034},
    {"name": "Batch Number", "key": "batch_number", "priority": "LOW", "weight": 0.033},
    {"name": "Unit Sale Price", "key": "unit_sale_price", "priority": "LOW", "weight": 0.033},
]


def calculate_score(extraction: ExtractionResult) -> ComplianceScore:
    """Calculate compliance score based on 10 key parameters.
    
    Args:
        extraction: Extracted fields from OCR processing
        
    Returns:
        ComplianceScore with total score, grade, and parameter details
    """
    parameters = []
    
    for param_def in PARAMETERS:
        field_name = param_def["key"]
        present = extraction.has(field_name)
        
        if present:
            field_val = extraction.get(field_name)
            value = field_val.value if field_val else "Present"
            # Score based on confidence if available
            confidence = getattr(field_val, 'confidence', 0.9) if field_val else 0.9
            score = min(1.0, confidence)
        else:
            value = "Not Detected"
            score = 0.0
        
        points = param_def["weight"] * score * 100
        
        parameters.append(ParameterScore(
            name=param_def["name"],
            priority=param_def["priority"],
            weight=param_def["weight"],
            present=present,
            value=value,
            score=score,
            points=points,
        ))
    
    total_score = sum(p.points for p in parameters)
    grade = _calculate_grade(total_score)
    
    return ComplianceScore(
        total_score=total_score,
        grade=grade,
        parameters=parameters,
        pass_threshold=80.0,
    )


def _calculate_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def get_grade_description(grade: str) -> str:
    """Return description for grade."""
    descriptions = {
        "A+": "Excellent - Fully Compliant",
        "A": "Good - Compliant",
        "B": "Satisfactory - Mostly Compliant",
        "C": "Needs Improvement",
        "D": "Poor - Significant Issues",
        "F": "Fail - Non-Compliant",
    }
    return descriptions.get(grade, "Unknown")
