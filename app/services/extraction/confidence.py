"""Confidence evaluation — ``app/services/extraction/confidence.py`` (Phase 9).

Combines OCR confidence with per-field extractor confidence into a single
``confidence`` carried by each FieldEvidence. The rule is deliberately
conservative: the field is only as trustworthy as its weakest signal.

    combined = ocr_confidence * extractor_confidence

A CAP on the extractor confidence (0.95) prevents a perfect regex from
hiding genuinely poor OCR.
"""

_DEFAULT_EXTRACTOR_CONFIDENCE = 0.85
_MAX_EXTRACTOR_CONFIDENCE = 0.95


def combine(ocr_confidence, extractor_confidence=None):
    """Return combined field confidence in [0, 1]."""
    base = float(ocr_confidence) if ocr_confidence is not None else 0.5
    ex = extractor_confidence
    if ex is None:
        ex = _DEFAULT_EXTRACTOR_CONFIDENCE
    ex = min(float(ex), _MAX_EXTRACTOR_CONFIDENCE)
    return round(base * ex, 4)


def field_status(combined: float, present: bool, partial: bool = False):
    """Derive a FieldStatus from confidence + presence.

    Missing evidence -> MISSING. A present-but-partial value -> UNCERTAIN.
    A believably present value -> DETECTED.
    """
    from app.services.extraction.evidence import FieldStatus

    if not present:
        return FieldStatus.MISSING
    if partial or combined < 0.5:
        return FieldStatus.UNCERTAIN
    return FieldStatus.DETECTED