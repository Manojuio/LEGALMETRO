"""OCR sub-package of the engine rebuild.

Phase 4: engine.py — single-pass EasyOCR engine returning evidence blocks.
"""

from app.services.ocr.engine import (
    OCREngineError,
    OCRNoTextError,
    run_ocr,
    normalize_bbox,
)

__all__ = ["OCREngineError", "OCRNoTextError", "run_ocr", "normalize_bbox"]