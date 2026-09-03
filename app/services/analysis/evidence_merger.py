"""Multi-image evidence merging + conflict detection.

``app/services/analysis/evidence_merger.py`` (Phases 10 & 11).

An analysis has FRONT/BACK/SIDE/OTHER images producing overlapping evidence
(e.g. MRP on the front and again on the back). This module:

    - Phase 10: merges per-image FieldCollections into one per-field set,
      keeping every candidate value + its source image/bbox.
    - Phase 11: flags a CONFLICTING value when two candidates for the same
      scalar field disagree on the normalized value (case/unit-insensitive).

The merged output is a dict of field_name -> list[FieldEvidence], ordered by
confidence, plus a per-field decided value and status.
"""

from app.services.extraction.evidence import FieldStatus


def merge_collections(collections) -> dict:
    """Merge a list of FieldCollection (one per image) into field_name->list.

    Returns a dict: {field_name: [FieldEvidence, ...]} ordered by confidence
    descending. All evidence stays traceable to its source image/bbox.
    """
    merged: dict[str, list] = {}
    for col in collections:
        for field_name, evidences in col.fields.items():
            queue = merged.setdefault(field_name, [])
            queue.extend(evidences)
    for field_name in merged:
        merged[field_name].sort(key=lambda e: e.confidence, reverse=True)
    return merged


def _scalar(ev) -> tuple:
    """Normalized comparable key for a scalar field's value."""
    if ev.numeric is not None:
        return ("num", ev.numeric)
    if ev.value is None:
        return ("none", None)
    return ("str", str(ev.value).strip().lower().rstrip("."))


def _is_scalar(field_name: str) -> bool:
    return field_name in {
        "mrp",
        "unit_sale_price",
        "net_quantity",
        "batch_number",
        "country_of_origin",
        "packing_date",
        "best_before_date",
        "expiry_date",
    }


def resolve_conflicts(merged: dict) -> dict:
    """Partition multi-value scalar fields: best value + status.

    For scalar fields with multiple different candidate VALUES, the field is
    marked CONFLICTING (the analysis must REVIEW). For every field we keep a
    ``decision`` with the chosen value (highest confidence) and its status.

    Returns a dict: {
        field_name: {value, numeric, unit, source_text, image_id, bbox,
                     confidence, status, candidates: [dict, ...]}
    }
    """
    resolved = {}
    for field_name, evidences in merged.items():
        decision = _decide_single(field_name, evidences)
        resolved[field_name] = decision
    return resolved


def _decide_single(field_name: str, evidences: list) -> dict:
    from app.services.extraction.evidence import FieldStatus

    best = max(evidences, key=lambda e: (e.confidence, e.value is not None))
    keys = {_scalar(e) for e in evidences if e.status != FieldStatus.UNCERTAIN and e.status != "UNCERTAIN"}
    conflict = False
    if _is_scalar(field_name) and len(keys) > 1:
        conflict = True

    status = FieldStatus.DETECTED
    if conflict:
        status = FieldStatus.CONFLICTING
    elif best.status in (FieldStatus.UNCERTAIN, "UNCERTAIN") or best.value is None:
        status = FieldStatus.UNCERTAIN

    return {
        "field_name": field_name,
        "value": best.value,
        "numeric": best.numeric,
        "unit": best.unit,
        "source_text": best.source_text,
        "image_id": best.image_id,
        "bbox": best.bbox,
        "confidence": best.confidence,
        "status": status.value,
        "candidates": [_candidate_dict(e) for e in evidences],
    }


def _candidate_dict(ev) -> dict:
    return {
        "value": ev.value,
        "numeric": ev.numeric,
        "unit": ev.unit,
        "source_text": ev.source_text,
        "image_id": ev.image_id,
        "bbox": ev.bbox,
        "confidence": ev.confidence,
        "status": ev.status.value if hasattr(ev.status, "value") else ev.status,
    }