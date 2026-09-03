"""End-to-end OCR orchestrator — ``app/services/analysis/ocr_pipeline.py``.

Phases 13 & 14. This is the single place the image → OCR → line reconstruction
→ field extraction → merge/conflict pipeline runs, replacing the duplicated
loops that used to live in ``api/analysis.py`` and ``compliance_service.py``.

Beyond producing evidence, it:
    - persists OCR results (evidence) into ``OCRResult`` rows,
    - persists extracted fields into ``ExtractedField`` rows with source_image,
    - isolates per-image failures (one corrupt image never aborts the run),
    - records per-stage timing for performance measurement (Phase 14).

It NEVER decides compliance. The evidence it returns is consumed by the
existing compliance/rule engine.
"""

import time
from dataclasses import dataclass, field

import logging

from app.core.config import get_settings
from app.models import analysis as models
from app.services import image_service
from app.services.image import preprocessing
from app.services.image.quality import assess_bytes
from app.services.ocr import engine as ocr_engine
from app.services.ocr import normalizer
from app.services.ocr.line_builder import build_lines, join_lines
from app.services.extraction.fields import extract_fields
from app.services.analysis import evidence_merger

logger = logging.getLogger(__name__)

# errors we treat as engine (not corruption) failures per image
_ENGINE_ERRORS = (ocr_engine.OCREngineError,)


@dataclass
class ImageStageTimings:
    image_id: str
    processing_ms: int = 0
    ocr_ms: int = 0
    line_ms: int = 0
    extraction_ms: int = 0
    total_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "processing_ms": self.processing_ms,
            "ocr_ms": self.ocr_ms,
            "line_ms": self.line_ms,
            "extraction_ms": self.extraction_ms,
            "total_ms": self.total_ms,
        }


@dataclass
class PipelineOutput:
    """Result of running the OCR pipeline over one analysis."""

    status: str = "completed"
    text_blocks: list = field(default_factory=list)
    collections: list = field(default_factory=list)
    merged: dict = field(default_factory=dict)
    resolved: dict = field(default_factory=dict)
    per_image: list = field(default_factory=list)
    raw_text: str = ""
    normalized_text: str = ""
    timings: list = field(default_factory=list)
    failure_count: int = 0


def _stage_count(fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    return result, int((time.perf_counter() - start) * 1000)


def run_pipeline(analysis, db) -> PipelineOutput:
    """Run validate → quality → preprocess → OCR → lines → extract → merge.

    Returns a PipelineOutput with full evidence. Persists OCRResult +
    ExtractedField rows. Per-image errors are isolated and counted, never
    raised.
    """
    settings = get_settings()
    images = (
        db.query(models.ProductImage)
        .filter(models.ProductImage.analysis_id == analysis.id)
        .all()
    )
    out = PipelineOutput()
    collections = []

    for img in images:
        t_img = ImageStageTimings(image_id=img.id)
        # --- read + validate ---
        try:
            with open(img.file_path, "rb") as fh:
                data = fh.read()
            image_service.validate_image_bytes(data, img.filename)
        except Exception as exc:
            logger.warning("Image %s validation failed: %s", img.id, exc)
            out.failure_count += 1
            continue

        # --- quality assessment (Phase 2) ---
        try:
            quality = assess_bytes(data)
        except Exception as exc:
            logger.warning("Quality assessment failed for %s: %s", img.id, exc)
            quality = None

        # --- preprocessing (Phase 3) ---
        try:
            pre, t_img.processing_ms = _stage_count(
                preprocessing.preprocess_bytes, data
            )
        except Exception as exc:
            logger.warning("Preprocessing failed for %s: %s", img.id, exc)
            out.failure_count += 1
            continue

        # --- OCR (Phase 4/5) ---
        blocks = []
        try:
            result, t_img.ocr_ms = _stage_count(
                ocr_engine.run_ocr, pre, img.id
            )
            blocks = normalizer.normalize_blocks(result.blocks)
            engine_used = result.engine
            conf_score = result.confidence_score
            proc_ms = result.processing_time_ms
        except _ENGINE_ERRORS as exc:
            logger.warning("OCR failed for image %s: %s", img.id, exc.code)
            out.failure_count += 1
            # persist an empty OCR result as evidence of the failure
            db.add(
                models.OCRResult(
                    analysis_id=analysis.id,
                    image_id=img.id,
                    raw_text="",
                    text_blocks=[],
                    confidence_score=0.0,
                    processing_time_ms=0,
                    ocr_engine="easyocr",
                )
            )
            continue
        except Exception as exc:
            logger.warning("Unknown OCR failure for %s: %s", img.id, exc)
            out.failure_count += 1
            continue

        # --- line reconstruction (Phase 6) ---
        lines, t_img.line_ms = _stage_count(
            build_lines, blocks, pre.height
        )
        line_text = join_lines(lines)

        # --- field extraction (Phases 7–9) ---
        try:
            col, t_img.extraction_ms = _stage_count(
                extract_fields, lines, img.id
            )
        except Exception as exc:
            logger.warning("Extraction failed for %s: %s", img.id, exc)
            col = None

        t_img.total_ms = (
            t_img.processing_ms + t_img.ocr_ms + t_img.line_ms + t_img.extraction_ms
        )
        out.timings.append(t_img.to_dict())

        # --- accumulate per-image evidence ---
        text_blocks = [
            {
                "text": b.text,
                "raw_text": b.raw_text,
                "normalized_text": b.normalized_text,
                "confidence": b.confidence,
                "bbox": b.bbox,
            }
            for b in blocks
        ]
        out.text_blocks.append(
            {
                "image_id": img.id,
                "position": img.image_position.value if img.image_position else "OTHER",
                "blocks": text_blocks,
                "raw_text": result.raw_text,
                "normalized_text": line_text,
                "confidence": conf_score,
                "engine": engine_used,
                "processing_time_ms": proc_ms,
                "steps_applied": list(pre.steps_applied),
            }
        )
        if col is not None:
            collections.append(col)

        # --- persist OCR evidence ---
        db.add(
            models.OCRResult(
                analysis_id=analysis.id,
                image_id=img.id,
                raw_text=result.raw_text,
                text_blocks=text_blocks,
                confidence_score=conf_score,
                processing_time_ms=proc_ms,
                ocr_engine=engine_used,
            )
        )

        out.raw_text = result.raw_text if not out.raw_text else out.raw_text + "\n" + result.raw_text
        out.normalized_text = line_text if not out.normalized_text else out.normalized_text + "\n" + line_text

    # --- merge + conflict detection (Phases 10/11) ---
    out.collections = collections
    out.merged = evidence_merger.merge_collections(collections)
    out.resolved = evidence_merger.resolve_conflicts(out.merged)

    db.commit()

    # --- persist extracted fields (evidence-aware) ---
    persist_extracted_fields(analysis, out.resolved, db)

    if not images:
        out.status = "empty"
    elif out.failure_count and not out.text_blocks:
        out.status = "failed"
    return out


def persist_extracted_fields(analysis, resolved, db):
    """Write resolved fields into ExtractedField rows (source_image aware)."""
    db.query(models.ExtractedField).filter(
        models.ExtractedField.analysis_id == analysis.id
    ).delete()
    for field_name, d in resolved.items():
        db.add(
            models.ExtractedField(
                analysis_id=analysis.id,
                field_name=field_name,
                field_value=d.get("value"),
                field_value_numeric=d.get("numeric"),
                confidence=d.get("confidence"),
                source_text=d.get("source_text") or "",
                source_image_id=d.get("image_id"),
                extraction_method=f"evidence-{d.get('status', 'DETECTED').lower()}",
            )
        )
    db.commit()