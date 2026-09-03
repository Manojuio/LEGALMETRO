"""Field statuses — ``app/services/extraction/evidence.py`` (Phase 9).

A field extracted by the engine carries privileged evidence:
    - *what* it is (field_name)
    - *the text it came from* (source_text)
    - *where it was found* (image_id + bbox)
    - *how confident OCR was* (ocr_confidence)
    - *how confident the extractor was* (extraction_confidence)
    - *its state* (status)

Status values:
    DETECTED      — a believable value was extracted from evidence
    UNCERTAIN     — partial/unreliable value; the validator should REVIEW
    MISSING       — the expected label was not found; absent from evidence
    CONFLICTING   — multiple incompatible values were seen across images
"""

from enum import Enum


class FieldStatus(str, Enum):
    DETECTED = "DETECTED"
    UNCERTAIN = "UNCERTAIN"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"


class FieldEvidence:
    """Evidence record for a single extracted field value."""

    __slots__ = (
        "field_name",
        "value",
        "numeric",
        "unit",
        "source_text",
        "image_id",
        "bbox",
        "confidence",
        "extraction_confidence",
        "status",
    )

    def __init__(
        self,
        field_name: str,
        value=None,
        numeric=None,
        unit=None,
        source_text=None,
        image_id=None,
        bbox=None,
        confidence=0.0,
        extraction_confidence=None,
        status=FieldStatus.DETECTED,
    ):
        self.field_name = field_name
        self.value = value
        self.numeric = numeric
        self.unit = unit
        self.source_text = source_text
        self.image_id = image_id
        self.bbox = list(bbox) if bbox else None
        self.confidence = round(float(confidence), 4)
        self.extraction_confidence = (
            round(float(extraction_confidence), 4)
            if extraction_confidence is not None
            else None
        )
        self.status = status if isinstance(status, FieldStatus) else FieldStatus(status)

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "numeric": self.numeric,
            "unit": self.unit,
            "source_text": self.source_text,
            "image_id": self.image_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "extraction_confidence": self.extraction_confidence,
            "status": self.status.value,
        }


class FieldCollection:
    """Holds all extracted fields for one image (or one analysis)."""

    __slots__ = ("fields", "image_id")

    def __init__(self, image_id=None):
        self.image_id = image_id
        self.fields: dict[str, list[FieldEvidence]] = {}

    def add(self, evidence: FieldEvidence):
        self.fields.setdefault(evidence.field_name, []).append(evidence)

    def best(self, field_name: str) -> FieldEvidence | None:
        """Return the highest-confidence evidence for a field (or None)."""
        items = self.fields.get(field_name) or []
        if not items:
            return None
        return max(items, key=lambda e: e.confidence)

    def names(self) -> set[str]:
        return set(self.fields.keys())