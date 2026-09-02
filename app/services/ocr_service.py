"""OCR service based on EasyOCR.

OCR is treated strictly as EVIDENCE EXTRACTION, never as a compliance
decision maker. This service:

1. Receives preprocessed image bytes
2. Runs EasyOCR with configured language + GPU settings
3. Normalizes the raw EasyOCR output into structured blocks:
   - text
   - confidence
   - bounding box (x, y, w, h)
4. Computes an aggregate confidence score for the image

EasyOCR is a heavy model. It is loaded lazily and cached as a module-level
singleton so repeated calls do not reload the model.

No legal logic lives here.
"""

import time
from dataclasses import dataclass, field

import numpy as np

from app.core.config import get_settings


@dataclass
class OCRBlock:
    """One recognized text region."""

    text: str
    confidence: float
    bbox: list[int]  # [x, y, width, height]


@dataclass
class OCRResult:
    """Normalized OCR output for a single image."""

    blocks: list[OCRBlock] = field(default_factory=list)
    raw_text: str = ""
    lenient_text: str = ""
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    engine: str = "easyocr"
    steps_applied: list[str] = field(default_factory=list)


_reader = None


def _get_reader():
    """Lazily instantiate and cache the EasyOCR reader."""
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
    """Convert EasyOCR's 4-corner polygon into [x, y, w, h].

    EasyOCR returns a list of four [x, y] points. We take the min x/y as
    origin and compute width/height from the extents.
    """
    if not points:
        return [0, 0, 0, 0]
    xs = [int(round(p[0])) for p in points]
    ys = [int(round(p[1])) for p in points]
    x = min(xs)
    y = min(ys)
    w = max(xs) - x
    h = max(ys) - y
    return [x, y, w, h]


def run_ocr(image_data: np.ndarray, steps_applied: list[str] | None = None) -> OCRResult:
    """Run EasyOCR on a preprocessed (grayscale/color) numpy image.

    image_data: the preprocessed image (color or grayscale) as numpy array.

    Returns a normalized OCRResult.
    """
    reader = _get_reader()
    start = time.perf_counter()

    raw = reader.readtext(image_data)

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    settings = get_settings()
    min_conf = settings.OCR_MIN_CONFIDENCE

    blocks: list[OCRBlock] = []
    confidence_total = 0.0
    for item in raw:
        points, text, conf = item
        blocks.append(
            OCRBlock(
                text=str(text).strip(),
                confidence=float(conf),
                bbox=normalize_bbox(points),
            )
        )
        confidence_total += float(conf)

    # Blocks above min confidence feed the "clean" raw_text used for
    # extraction. However, small-print declarations on many real packages are
    # read at low OCR confidence yet carry genuine data (MRP, net qty, batch,
    # dates). So we ALSO keep a lenient text-pass built from every non-empty
    # block; extraction regexes naturally filter out OCR noise, so this
    # recovers genuine but low-confidence declarations without polluting
    # decisions (validators still sanity-check values).
    non_empty = [b for b in blocks if b.text]
    if non_empty:
        confidence_score = sum(b.confidence for b in non_empty) / len(non_empty)
    else:
        confidence_score = 0.0

    # Confident-only text (used elsewhere)
    confident_non_empty = [b for b in blocks if b.text and b.confidence >= min_conf]
    raw_text_confident = "\n".join(b.text for b in confident_non_empty)

    # Lenient text: every readable token, grouped into visual lines by
    # vertical (row) proximity, then left-to-right within each row. This
    # preserves line structure for line-based extraction heuristics while
    # still including low-confidence-but-genuine declarations.
    ordered = sorted(
        (b for b in blocks if b.text),
        key=lambda b: (b.bbox[1] if b.bbox else 0, b.bbox[0] if b.bbox else 0),
    )
    lines: list[list[str]] = []
    current_row = None
    current_row_y = None
    for b in ordered:
        y = b.bbox[1] if b.bbox else 0
        if current_row_y is None or abs(y - current_row_y) > 15:
            current_row = [b.text]
            current_row_y = y
            lines.append(current_row)
        else:
            current_row.append(b.text)
    raw_text_lenient = "\n".join(" ".join(row) for row in lines)

    return OCRResult(
        blocks=blocks,
        raw_text=raw_text_confident,
        lenient_text=raw_text_lenient,
        confidence_score=round(confidence_score, 4),
        processing_time_ms=elapsed_ms,
        steps_applied=list(steps_applied or []),
    )
