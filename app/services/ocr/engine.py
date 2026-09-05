"""Phases 4/5 single-pass EasyOCR engine — ``app/services/ocr/engine.py``.

Replaces the old 6-variant / 3-pass fusion in ``ocr_service.py`` with a
deterministic **single baseline pass** (per the Phase 0 audit). EasyOCR runs
once over one preprocessed grayscale image and returns cleaned, evidence-first
blocks carrying the source ``image_id`` and raw/normalized text.

Engine principles:
    - OCR is **evidence extraction only**, never a compliance decision.
    - The original image is never modified or referenced after decoding.
    - Every block keeps ``raw_text`` (verbatim) + ``normalized_text`` (joined,
      whitespace-normalized) so nothing from the model is lost.
    - One engine failure on one image must never abort an analysis (error
      isolation is the caller's responsibility; we raise a typed error).
    - Empty/blank OCR output raises ``OCRNoTextError`` (``OCR_NO_TEXT``).

The EasyOCR reader is loaded lazily and cached as a module-level singleton so
repeated calls never reload the model.
"""

import time
from dataclasses import dataclass, field

import numpy as np

from app.core.config import get_settings

# Stable error codes (documented in docs/OCR_ENGINE.md).
OCR_FAILED = "OCR_FAILED"
OCR_NO_TEXT = "OCR_NO_TEXT"


class OCREngineError(Exception):
    """Base error raised by the OCR engine. Carries a stable ``.code``."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class OCRNoTextError(OCREngineError):
    """Raised when OCR finds no usable text on a processed image."""

    def __init__(self, message: str = "No usable text detected by OCR."):
        super().__init__(OCR_NO_TEXT, message)


@dataclass
class OCRBlock:
    """One recognized text region, with full evidence traceability.

    ``bbox`` is ``[x, y, w, h]`` in **processed** (OCR-input) space. Map back
    to original-image space with ``PreprocessedImage.bbox_to_original``.
    """

    image_id: str
    text: str
    confidence: float
    bbox: list[int]  # [x, y, width, height]
    engine: str = "easyocr"
    raw_text: str = ""
    normalized_text: str = ""

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "text": self.text,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence": round(float(self.confidence), 4),
            "bbox": [int(v) for v in self.bbox],
            "engine": self.engine,
        }


@dataclass
class OCREngineResult:
    """Normalized output for a single (single-pass) image."""

    blocks: list[OCRBlock] = field(default_factory=list)
    raw_text: str = ""
    normalized_text: str = ""
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    engine: str = "easyocr"
    block_count: int = 0

    def to_dict(self) -> dict:
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence_score": round(float(self.confidence_score), 4),
            "processing_time_ms": self.processing_time_ms,
            "engine": self.engine,
            "block_count": self.block_count,
        }


_reader = None


def _get_reader():
    """Lazily instantiate and cache the EasyOCR reader (module singleton)."""
    global _reader
    if _reader is None:
        settings = get_settings()
        import easyocr

        _reader = easyocr.Reader(
            settings.OCR_LANGUAGE,
            gpu=settings.OCR_GPU,
            verbose=False,
        )
    return _reader


def normalize_bbox(points) -> list[int]:
    """Convert EasyOCR's 4-corner polygon into ``[x, y, w, h]``."""
    if not points:
        return [0, 0, 0, 0]
    xs = [int(round(p[0])) for p in points]
    ys = [int(round(p[1])) for p in points]
    x = min(xs)
    y = min(ys)
    w = max(xs) - x
    h = max(ys) - y
    return [x, y, w, h]


def _normalize_text(raw: str) -> str:
    """Whitespace-normalize a raw OCR reading (join away multiple spaces)."""
    return " ".join(raw.split())


def run_ocr(image_data, image_id: str = "") -> OCREngineResult:
    """Run a single EasyOCR pass on one processed image.

    ``image_data`` is a ``PreprocessedImage`` (its ``.processed`` grayscale
    array is used) or a plain 2D/3D numpy array for convenience. ``image_id``
    is recorded on every block for traceability.

    Occlusion / low-confidence blocks are never silently dropped: every
    block is returned as evidence (consumers apply ``OCR_MIN_CONFIDENCE``).
    If no text is detected at all, raises :class:`OCRNoTextError`.
    """
    arr = _as_grayscale(image_data)
    reader = _get_reader()
    start = time.perf_counter()

    try:
        items = reader.readtext(arr)
    except OCREngineError:
        raise
    except Exception as exc:  # EasyOCR/torch errors wrap into OCR_FAILED
        raise OCREngineError(OCR_FAILED, f"OCR engine failed: {exc}") from exc

    blocks: list[OCRBlock] = []
    for points, text, conf in items:
        raw = str(text).strip()
        if not raw:
            continue
        blocks.append(
            OCRBlock(
                image_id=image_id,
                text=raw,
                raw_text=raw,
                normalized_text=_normalize_text(raw),
                confidence=float(conf),
                bbox=normalize_bbox(points),
            )
        )

    if not blocks:
        raise OCRNoTextError()

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Deterministic line join: sort by vertical center then horizontal.
    blocks.sort(
        key=lambda b: (
            (b.bbox[1] + b.bbox[3] // 2),
            b.bbox[0],
        )
    )
    raw_text = "\n".join(b.raw_text for b in blocks)
    normalized_text = "\n".join(b.normalized_text for b in blocks)
    score = sum(b.confidence for b in blocks) / len(blocks)

    return OCREngineResult(
        blocks=blocks,
        raw_text=raw_text,
        normalized_text=normalized_text,
        confidence_score=round(score, 4),
        processing_time_ms=elapsed_ms,
        block_count=len(blocks),
    )


def _as_grayscale(image_data) -> np.ndarray:
    """Extract a grayscale ndarray from a PreprocessedImage or raw array."""
    processed = getattr(image_data, "processed", None)
    if processed is not None:
        arr = np.asarray(processed)
    else:
        arr = np.asarray(image_data)

    if arr.size == 0:
        raise OCREngineError(OCR_FAILED, "OCR received an empty image.")
    if arr.ndim == 3:
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]
        if arr.shape[2] == 3:
            import cv2

            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    if arr.ndim != 2:
        raise OCREngineError(OCR_FAILED, "OCR requires a grayscale (H, W) image.")
    return arr