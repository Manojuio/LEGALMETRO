"""OCR service based on EasyOCR with multi-variant fusion.

OCR is treated strictly as EVIDENCE EXTRACTION, never as a compliance
decision maker. This service:

1. Receives a PreprocessedImage (or raw numpy array) holding several OpenCV
   "variants" of the same image (clean grayscale, CLAHE contrast-enhanced,
   upscaled, deskewed, Otsu-binarized, inverted).
2. Runs EasyOCR over the best few variants with configured language + GPU.
3. Fuses the per-region results: for each text line it keeps the highest
   confidence reading, so whichever variant read a region best wins.
4. Normalizes output into structured blocks:
   - text, confidence, bounding box (x, y, w, h)
5. Computes an aggregate confidence score for the image.

EasyOCR is a heavy model. It is loaded lazily and cached as a module-level
singleton so repeated calls do not reload the model.

No legal logic lives here.
"""

import time
from dataclasses import dataclass, field

import numpy as np

from app.core.config import get_settings
from app.services.image_service import ImageVariant


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

# Preference order for picking which variants to actually run OCR on.
_VARIANT_PRIORITY = ["gray", "clahe", "upscaled", "deskew", "otsu", "invert"]
# Keep the runtime bounded: run EasyOCR on at most this many variants.
MAX_OCR_PASSES = 3


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
    """Convert EasyOCR's 4-corner polygon into [x, y, w, h]."""
    if not points:
        return [0, 0, 0, 0]
    xs = [int(round(p[0])) for p in points]
    ys = [int(round(p[1])) for p in points]
    x = min(xs)
    y = min(ys)
    w = max(xs) - x
    h = max(ys) - y
    return [x, y, w, h]


def _pick_variants(processed) -> list:
    """Choose up to MAX_OCR_PASSES variants to run OCR on, baseline first."""
    variants = list(getattr(processed, "variants", None) or [])
    if not variants:
        # Backward compat: caller passed a raw grayscale image.
        variants = [ImageVariant("gray", np.asarray(processed))]
    order = {name: i for i, name in enumerate(_VARIANT_PRIORITY)}
    variants.sort(key=lambda v: order.get(v.name, 99))
    # Ensure the clean grayscale baseline is always first if available.
    base = next((v for v in variants if v.name == "gray"), variants[0])
    rest = [v for v in variants if v is not base]
    selected = [base] + rest[: MAX_OCR_PASSES - 1]
    return selected


def _run_pass(reader, image: np.ndarray):
    """Run EasyOCR once and return raw items, plus pixel scale metadata."""
    return reader.readtext(image)


def _merge_results(per_variant, baseline_shape, min_conf):
    """Fuse per-variant OCR detections into a single reading.

    Strategy: normalize every block's coordinates to the baseline image
    coordinate system, cluster them into visual lines, and within each line
    drop overlapping duplicates keeping the highest-confidence text. This way
    whichever variant read a given region best contributes to the final text.
    """
    base_h, base_w = baseline_shape[:2]
    band_tol = max(12, int(base_h * 0.018))

    # Normalized records with coordinates scaled back to baseline space.
    records = []
    for variant_result in per_variant:
        scale_x = base_w / variant_result["width"]
        scale_y = base_h / variant_result["height"]
        for item in variant_result["items"]:
            points, text, conf = item
            x, y, w, h = normalize_bbox(points)
            records.append(
                {
                    "text": str(text).strip(),
                    "conf": float(conf),
                    "x": int(x * scale_x),
                    "y": int(y * scale_y),
                    "w": int(w * scale_x),
                    "h": int(h * scale_y),
                    "yc": int(y * scale_y) + int(h * scale_y) // 2,
                }
            )

    records = [r for r in records if r["text"]]
    records.sort(key=lambda r: (r["yc"], r["x"]))

    # Cluster into lines.
    lines = []
    for r in records:
        placed = False
        for line in lines:
            if abs(r["yc"] - line[0]["yc"]) <= band_tol:
                line.append(r)
                placed = True
                break
        if not placed:
            lines.append([r])

    # Within each line, drop horizontally-overlapping duplicates (keep best).
    def h_overlap(a, b):
        a_l, a_r = a["x"], a["x"] + a["w"]
        b_l, b_r = b["x"], b["x"] + b["w"]
        inter = max(0, min(a_r, b_r) - max(a_l, b_l))
        shorter = min(a["w"], b["w"]) or 1
        return (inter / shorter) > 0.3

    final_lines = []
    for line in lines:
        line = sorted(line, key=lambda r: r["x"])
        kept = []
        for r in line:
            dup = next((k for k in kept if h_overlap(k, r)), None)
            if dup is not None:
                if r["conf"] > dup["conf"]:
                    kept[kept.index(dup)] = r
            else:
                kept.append(r)
        kept.sort(key=lambda r: r["x"])
        final_lines.append(kept)

    blocks: list[OCRBlock] = []
    for line in final_lines:
        for r in line:
            blocks.append(
                OCRBlock(
                    text=r["text"],
                    confidence=r["conf"],
                    bbox=[r["x"], r["y"], r["w"], r["h"]],
                )
            )

    # Text passes: confident-only and lenient (every readable token).
    confident_lines = []
    lenient_lines = []
    for line in final_lines:
        conf_ok = [r for r in line if r["conf"] >= min_conf]
        if conf_ok:
            confident_lines.append(" ".join(r["text"] for r in conf_ok))
        lenient_lines.append(" ".join(r["text"] for r in line))

    raw_text = "\n".join(confident_lines)
    lenient_text = "\n".join(lenient_lines)

    confident_blocks = [b for b in blocks if b.confidence >= min_conf]
    score = (
        sum(b.confidence for b in confident_blocks) / len(confident_blocks)
        if confident_blocks
        else 0.0
    )

    return blocks, raw_text, lenient_text, score


def run_ocr(image_data, steps_applied: list[str] | None = None) -> OCRResult:
    """Run EasyOCR across the best image variants and fuse the result.

    image_data: a PreprocessedImage (preferred) or a plain grayscale numpy
    array for backward compatibility.

    Returns a normalized OCRResult.
    """
    reader = _get_reader()
    start = time.perf_counter()

    settings = get_settings()
    min_conf = settings.OCR_MIN_CONFIDENCE

    if hasattr(image_data, "variants"):
        pre = image_data
        baseline = getattr(pre, "grayscale", None)
        baseline_shape = baseline.shape if baseline is not None else next(
            (v.image.shape for v in getattr(pre, "variants", [])), (0, 0)
        )
    else:
        baseline_shape = np.asarray(image_data).shape

    selected = _pick_variants(image_data)

    per_variant = []
    for v in selected:
        img = np.asarray(v.image)
        items = _run_pass(reader, img)
        per_variant.append(
            {
                "items": items,
                "width": img.shape[1],
                "height": img.shape[0],
            }
        )

    blocks, raw_text, lenient_text, confidence_score = _merge_results(
        per_variant, baseline_shape, min_conf
    )

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return OCRResult(
        blocks=blocks,
        raw_text=raw_text,
        lenient_text=lenient_text,
        confidence_score=round(confidence_score, 4),
        processing_time_ms=elapsed_ms,
        steps_applied=list(steps_applied or []),
    )
