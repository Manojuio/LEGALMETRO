"""Image preprocessing — Phase 3 of the OCR engine rebuild.

Modular, config-gated preprocessing. The baseline path is deliberately
minimal — every extra operation must justify itself with measured OCR
improvement (Phase 15):

    decode (Pillow + EXIF orientation)
      → resize within configured maximum dimension (downscale only)
      → grayscale
      → light denoise (edge-preserving bilateral, only when noisy)
      → CLAHE contrast enhancement (only when required OR explicitly enabled)
      → deskew (ONLY when OCR_ENABLE_DESKEW=True)
      → threshold (ONLY when OCR_ENABLE_THRESHOLD=True)

THE ORIGINAL IMAGE IS NEVER MODIFIED. ``PreprocessedImage.original`` is the
decoded BGR frame exactly as received (oriented); ``.processed`` is a fresh
grayscale array for OCR. Scale factors are retained so OCR bounding boxes
can be mapped back to original-image coordinates — evidence traceability.

No OCR and no compliance logic here.
"""

import io
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.services.image.validator import IMAGE_DECODE_FAILED, ImageValidationError

# Denoise only kicks in above this gray variance (texture/noise heuristic).
_DENOISE_VARIANCE_TRIGGER = 2000.0

# Auto-CLAHE trigger: percentile contrast below this means the image is
# washed out and contrast enhancement "when required" applies (see
# quality.py contrast bands — 0.25 is the ACCEPTABLE/POOR boundary).
_LOW_CONTRAST_AUTO = 0.25

# Preprocessing option keys accepted by preprocess(image, options).
OPTION_KEYS = ("max_dim", "denoise", "clahe", "deskew", "threshold")

# threshold option values
THRESHOLD_OTSU = "otsu"
THRESHOLD_ADAPTIVE = "adaptive"


@dataclass
class PreprocessedImage:
    """Result of the preprocessing pipeline for one image.

    ``original`` is the decoded BGR frame, untouched. ``processed`` is the
    final grayscale array intended for OCR. Coordinates of OCR results on
    ``processed`` can be mapped back to ``original`` with ``bbox_to_original``.
    """

    original: np.ndarray
    processed: np.ndarray
    steps_applied: list[str] = field(default_factory=list)
    options_used: dict = field(default_factory=dict)

    # --- processed (OCR-input) dimensions ---
    @property
    def width(self) -> int:
        return int(self.processed.shape[1])

    @property
    def height(self) -> int:
        return int(self.processed.shape[0])

    # --- original dimensions ---
    @property
    def original_width(self) -> int:
        return int(self.original.shape[1])

    @property
    def original_height(self) -> int:
        return int(self.original.shape[0])

    # --- coordinate mapping processed -> original ---
    @property
    def scale_x(self) -> float:
        return self.original_width / self.width if self.width else 1.0

    @property
    def scale_y(self) -> float:
        return self.original_height / self.height if self.height else 1.0

    def bbox_to_original(self, bbox) -> list[int]:
        """Map an [x, y, w, h] box in processed space to original space."""
        x, y, w, h = (int(round(v)) for v in bbox)
        return [
            int(round(x * self.scale_x)),
            int(round(y * self.scale_y)),
            int(round(w * self.scale_x)),
            int(round(h * self.scale_y)),
        ]

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "steps_applied": list(self.steps_applied),
        }


def _resolve_options(options: dict | None) -> dict:
    """Merge caller options over settings-derived defaults."""
    settings = get_settings()
    defaults = {
        "max_dim": settings.OCR_MAX_IMAGE_DIM,
        "denoise": settings.OCR_DENOISE,
        "clahe": bool(settings.OCR_ENABLE_CLAHE),
        "deskew": bool(settings.OCR_ENABLE_DESKEW),
        "threshold": (
            THRESHOLD_OTSU if settings.OCR_ENABLE_THRESHOLD else None
        ),
    }
    merged = dict(defaults)
    if options:
        for key in OPTION_KEYS:
            if key in options:
                merged[key] = options[key]
    return merged


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------

def decode(data: bytes) -> np.ndarray:
    """Decode raw image bytes into an OpenCV BGR image.

    Pillow does the decoding (handles palette PNGs etc.) and EXIF orientation
    is applied, then the frame is converted to BGR. Raises
    ImageValidationError(IMAGE_DECODE_FAILED) on undecodable input.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # respect EXIF orientation
        rgb = np.array(img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(IMAGE_DECODE_FAILED, f"Cannot decode image: {exc}") from exc


# ---------------------------------------------------------------------------
# Individual operations (each returns a new array — never mutates input)
# ---------------------------------------------------------------------------

def resize_within_max(image: np.ndarray, max_dim: int, steps: list[str]) -> np.ndarray:
    """Downscale so the longest edge is <= max_dim. Aspect preserved."""
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return image
    scale = max_dim / longest
    out = cv2.resize(
        image,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_AREA,
    )
    steps.append(f"resize:{scale:.3f}")
    return out


def upscale_if_small(image: np.ndarray, min_height: int = 700, steps: list[str] | None = None) -> np.ndarray:
    """Upscale images where the shortest dimension is too small for OCR.

    Many package photos are taken at an angle or from a distance, resulting
    in small text that EasyOCR can't segment.  Upscaling to at least
    ``min_height`` px on the shortest edge gives the OCR engine more pixels
    to work with.  Only upscale (never shrink);  cap at 2x to avoid
    blowing up blurry images into very large arrays.
    """
    if steps is None:
        steps = []
    h, w = image.shape[:2]
    shortest = min(h, w)
    if shortest >= min_height:
        return image
    # scale so shortest edge reaches min_height, capped at 2x
    scale = min(2.0, min_height / shortest)
    new_w, new_h = int(w * scale), int(h * scale)
    out = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    steps.append(f"upscale:{scale:.2f}")
    return out


def to_grayscale(image: np.ndarray, steps: list[str]) -> np.ndarray:
    steps.append("grayscale")
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(gray: np.ndarray, steps: list[str]) -> np.ndarray:
    """Light edge-preserving denoise for noisy camera photos.

    Applied only when the gray variance suggests texture/noise worth
    smoothing; bilateral keeps text edges intact. Heuristic pending Phase 15
    measurement.
    """
    variance = float(np.var(gray))
    if variance < _DENOISE_VARIANCE_TRIGGER:
        return gray
    steps.append("denoise:bilateral")
    return cv2.bilateralFilter(gray, 5, 50, 50)


def _percentile_contrast(gray: np.ndarray) -> float:
    p2, p98 = np.percentile(gray, (2, 98))
    return float(p98 - p2) / 255.0


def clahe(gray: np.ndarray, enabled: bool, steps: list[str]) -> np.ndarray:
    """CLAHE contrast enhancement.

    Applied when explicitly enabled, or automatically when the image is
    washed out (low percentile contrast) — the "contrast improvement when
    required" step of the baseline.
    """
    if enabled:
        steps.append("clahe:enabled")
    elif _percentile_contrast(gray) >= _LOW_CONTRAST_AUTO:
        return gray
    else:
        steps.append("clahe:auto")
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cl.apply(gray)


def estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate text-sheet skew in degrees via Hough line transform.

    Returns ~0.0 when no reliable angle is found (already straight, no
    text, or near-90 rotation which is out of scope here).
    """
    h, w = gray.shape[:2]
    small_h = max(480, int(h * 0.6))
    if small_h >= h:
        small = gray
    else:
        r = small_h / h
        small = cv2.resize(gray, (int(w * r), small_h), interpolation=cv2.INTER_AREA)
    thresh = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    lines = cv2.HoughLinesP(
        thresh, 1, np.pi / 180, threshold=80,
        minLineLength=max(20, small.shape[1] // 12), maxLineGap=8,
    )
    if lines is None or len(lines) == 0:
        return 0.0
    angles = []
    for line in lines.reshape(-1, 4):
        x1, y1, x2, y2 = (int(v) for v in line)
        if abs(x2 - x1) < 3:  # ignore near-vertical lines
            continue
        angles.append(float(np.degrees(np.arctan2(y2 - y1, x2 - x1))))
    if not angles:
        return 0.0
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.4 or abs(median_angle) > 35:
        return 0.0
    return median_angle


def deskew(gray: np.ndarray, steps: list[str], angle: float | None = None) -> np.ndarray:
    """Rotate the image so text lines are horizontal.

    Only invoked when deskew is enabled; the angle comes from
    estimate_skew_angle unless supplied. No-op (returns input) when no
    meaningful skew is found.
    """
    if angle is None:
        angle = estimate_skew_angle(gray)
    if not angle:
        return gray
    h, w = gray.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out = cv2.warpAffine(
        gray, rot, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    steps.append(f"deskew:{angle:.1f}")
    return out


def threshold(gray: np.ndarray, kind: str | None, steps: list[str]) -> np.ndarray:
    """Binarize when explicitly enabled (otsu or adaptive)."""
    if kind is None:
        return gray
    if kind == THRESHOLD_OTSU:
        steps.append("threshold:otsu")
        return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    if kind == THRESHOLD_ADAPTIVE:
        steps.append("threshold:adaptive")
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 10,
        )
    raise ValueError(f"Unknown threshold kind: {kind!r}")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def preprocess(image: np.ndarray, options: dict | None = None) -> PreprocessedImage:
    """Run the baseline preprocessing pipeline on a decoded BGR image.

    ``image`` must be a BGR ndarray (see ``decode``). The array is never
    modified: every operation returns a fresh array, and the original is
    retained for evidence traceability.
    """
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("preprocess expects a decoded BGR image (H, W, 3)")
    opts = _resolve_options(options)
    steps: list[str] = []

    original = np.ascontiguousarray(image)  # snapshot — never mutated below

    working = resize_within_max(original, int(opts["max_dim"]), steps)
    working = upscale_if_small(working, steps=steps)
    working = to_grayscale(working, steps)
    if opts["denoise"]:
        working = denoise(working, steps)
    working = clahe(working, bool(opts["clahe"]), steps)
    if opts["deskew"]:
        working = deskew(working, steps)
    working = threshold(working, opts["threshold"], steps)

    return PreprocessedImage(
        original=original,
        processed=working,
        steps_applied=steps,
        options_used={k: opts[k] for k in OPTION_KEYS},
    )


def preprocess_bytes(data: bytes, options: dict | None = None) -> PreprocessedImage:
    """Convenience: decode raw bytes then run the preprocessing pipeline."""
    return preprocess(decode(data), options)
