"""Debug visualization — ``app/services/ocr/visualization.py`` (Phase 12).

Draws OCR bounding boxes + text onto a copy of the processed (or original)
image so a developer can eyeball what the engine saw. Only used when
``OCR_ENABLE_DEBUG`` is on; never affects stored evidence.

Artifacts are written as PNG (or JPEG) under ``OCR_DEBUG_DIR``.
"""

import os
from pathlib import Path

import cv2

from app.core.config import get_settings


def draw_ocr_boxes(image, blocks, output_path=None):
    """Draw blocks onto a copy of ``image`` and return the annotated ndarray.

    ``image`` may be a BGR ndarray or grayscale (auto-converted to BGR).
    ``blocks`` are NormalizedBlock/OCRBlock/dicts exposing ``bbox`` + ``text``.

    If ``output_path`` is None, a default path under ``OCR_DEBUG_DIR`` is used.
    The image is never written unless ``OCR_ENABLE_DEBUG`` is True.
    """
    settings = get_settings()
    if not settings.OCR_ENABLE_DEBUG and output_path is None:
        return image  # debugging disabled — do nothing
    if hasattr(image, "processed"):
        arr = image.processed
    else:
        arr = image
    if arr.ndim == 2:
        vis = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    else:
        vis = arr.copy()

    for b in blocks:
        bbox = getattr(b, "bbox", b.get("bbox", []) if isinstance(b, dict) else [])
        text = getattr(b, "text", b.get("text", "") if isinstance(b, dict) else "")
        if not bbox or len(bbox) != 4:
            continue
        x, y, w, h = (int(v) for v in bbox)
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 200, 0), 2)
        if text:
            cv2.putText(
                vis, str(text)[:40], (x, max(12, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1,
            )

    if output_path is None:
        out_dir = settings.OCR_DEBUG_DIR
        out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / "ocr_boxes.png"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(output_path), vis)
    return vis