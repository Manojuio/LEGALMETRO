"""Image validation, preprocessing, and metadata extraction.

This service owns ALL image handling that is NOT OCR itself:
- validate uploaded bytes (type, size, integrity)
- read and decode an image with OpenCV
- preprocess an image to improve OCR accuracy
- extract metadata (dimensions, format)

OCR must NOT happen here. This is prep-only so the OCR service
can stay focused on text recognition.
"""

import io
import os
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.services.image import validator as image_validator
from app.services.image.validator import ImageValidationError

# NOTE (Phase 1): image validation now lives in
# app/services/image/validator.py (single source of truth, stable error
# codes, dimension checks). ImageValidationError is re-exported here for
# backward compatibility with existing callers and tests.


@dataclass
class ImageVariant:
    """One prepared representation of an image for OCR scoring/fusion."""

    name: str
    image: np.ndarray
    description: str = ""


@dataclass
class PreprocessedImage:
    """Result of preprocessing one image."""

    cv2_image: np.ndarray
    grayscale: np.ndarray  # primary representation (clean grayscale)
    width: int
    height: int
    steps_applied: list[str]
    variants: list = field(default_factory=list)  # list[ImageVariant]
    original_bytes: bytes | None = None


def validate_image_bytes(data: bytes, filename: str | None = None) -> dict:
    """Validate raw image bytes (delegates to image/validator.py).

    Kept as a thin wrapper so existing callers (save_upload, the upload
    endpoint, tests) keep working unchanged. Raises ImageValidationError
    (with a stable ``.code``) on failure.
    """
    return image_validator.validate_image_bytes(data, filename)


def decode_to_cv2(data: bytes) -> np.ndarray:
    """Decode image bytes into an OpenCV BGR image.

    Pillow is used for decoding so that formats OpenCV's imdecode
    may not prefer (e.g. palette PNGs) are handled, then converted.
    Returns None-safe: raises ImageValidationError on failure.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # respect EXIF orientation
        rgb = np.array(img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        raise ImageValidationError(f"Cannot decode image: {exc}") from exc


def ensure_upload_dir(analysis_id: str) -> Path:
    """Create and return the upload directory for an analysis.

    Convention: uploads/analysis_<id>/
    """
    settings = get_settings()
    base = settings.UPLOAD_DIR
    base.mkdir(parents=True, exist_ok=True)
    analysis_dir = base / f"analysis_{analysis_id}"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir


def save_upload(
    analysis_id: str,
    data: bytes,
    position: str,
    original_filename: str,
) -> tuple[Path, dict]:
    """Validate, decode, and store one uploaded image.

    Returns (file_path, metadata). Raises ImageValidationError on failure.
    """
    metadata = validate_image_bytes(data, original_filename)
    ensure_upload_dir(analysis_id)

    position = (position or "OTHER").lower()
    # Keep a safe, normalized filename
    ext = os.path.splitext(original_filename or "")[1].lower() or ".jpg"
    filename = f"{position}{ext}"
    file_path = Path("uploads") / f"analysis_{analysis_id}" / filename
    absolute = settings_path(file_path)

    with open(absolute, "wb") as fh:
        fh.write(data)

    metadata["saved_path"] = str(file_path)
    return absolute, metadata


def settings_path(relative: Path) -> Path:
    """Resolve a relative upload path against the project root.

    Uploads are stored relative for DB portability but written to an
    absolute path anchored at the working directory.
    """
    if relative.is_absolute():
        return relative
    return Path.cwd() / relative


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate text-sheet skew in degrees using Hough line transform.

    Returns ~0 when no reliable angle is found (straight or no text).
    """
    h, w = gray.shape[:2]
    small_h = max(480, int(h * 0.6))
    if small_h >= h:
        small = gray
    else:
        r = small_h / h
        small = cv2.resize(gray, (int(w * r), small_h), interpolation=cv2.INTER_AREA)
    thresh = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    lines = cv2.HoughLinesP(thresh, 1, np.pi / 180, threshold=80, minLineLength=max(20, small.shape[1] // 12), maxLineGap=8)
    if lines is None or len(lines) == 0:
        return 0.0
    lines = lines.reshape(-1, 4)
    angles = []
    for line in lines:
        x1, y1, x2, y2 = (int(v) for v in line)
        if abs(x2 - x1) < 3:  # ignore near-vertical lines
            continue
        deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        angles.append(deg)
    if not angles:
        return 0.0
    median_angle = float(np.median(angles))
    # Only correct small / medium skew; leave near-90 (image rotated) for the model.
    if abs(median_angle) < 0.4 or abs(median_angle) > 35:
        return 0.0
    return median_angle


def _deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    h, w = gray.shape[:2]
    center = (w / 2, h / 2)
    rot = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray, rot, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _clahe_enhance(gray: np.ndarray, clip: float = 2.0, tile: int = 8) -> np.ndarray:
    """Contrast-Limited Adaptive Histogram Equalization.

    Dynamic per-region contrast — the core OpenCV pattern for low-contrast /
    photo-captured labels and small print. Far more robust than a single
    fixed threshold because it adapts to local illumination gradients.
    """
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    return clahe.apply(gray)


def _build_variants(gray: np.ndarray, steps: list[str]) -> list:
    """Build a small set of image representations to OCR + fuse.

    Strategy per image (dynamic):
    - clean grayscale (baseline)
    - CLAHE contrast-enhanced (low-contrast / camera photos)
    - upscaled (tiny/small-print labels)
    - Otsu binarized (clean high-contrast print, fallback)
    - deskewed (rotated photos)
    - inverted (dark-background, light-text labels)
    """
    h, w = gray.shape[:2]
    mean_lum = float(np.mean(gray))
    variants = []

    variants.append(ImageVariant("gray", gray, "clean grayscale baseline"))
    steps.append("v:gray")

    # CLAHE contrast enhancement (adaptive local contrast)
    clahe = _clahe_enhance(gray)
    variants.append(ImageVariant("clahe", clahe, "CLAHE contrast enhanced"))
    steps.append("v:clahe")

    # Upscale small images so EasyOCR sees larger text
    if max(h, w) < 1500:
        scale = 2.0 if max(h, w) < 1100 else 1.5
        up = cv2.resize(
            gray, (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
        variants.append(ImageVariant("upscaled", up, f"upscaled {scale:.1f}x"))
        steps.append(f"v:upscaled:{scale:.1f}")

    # Otsu binarization fallback for clean, high-contrast printed labels
    otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    variants.append(ImageVariant("otsu", otsu, "Otsu binarized"))
    steps.append("v:otsu")

    # Deskew if there is measurable rotation
    angle = _estimate_skew_angle(gray)
    if angle:
        variants.append(ImageVariant("deskew", _deskew(gray, angle), f"deskewed {angle:.1f}deg"))
        steps.append(f"v:deskew:{angle:.1f}")

    # Dark background with light text → invert so text is dark-on-light
    if mean_lum < 90:
        inv = cv2.bitwise_not(gray)
        variants.append(ImageVariant("invert", inv, "inverted (dark bg)"))
        steps.append("v:invert")

    # De-duplicate variants that are byte-identical (e.g. CLAHE on an already
    # contrast-balanced image). Compare actual pixel data, not coarse stats.
    seen = set()
    uniq = []
    for v in variants:
        marker = hash(v.image.tobytes())
        if marker in seen:
            continue
        seen.add(marker)
        uniq.append(v)
    return uniq


def preprocess(data: bytes) -> PreprocessedImage:
    """Run the dynamic preprocessing pipeline on an image.

    Produces a set of OpenCV variants tuned to the specific image (contrast,
    size, skew, background) and hands them to the OCR service, which fuses
    the highest-quality recognition per region. This replaces the old
    single fixed binarization that discarded text detail for EasyOCR.
    """
    settings = get_settings()
    cv2_img = decode_to_cv2(data)
    steps: list[str] = []

    max_dim = getattr(settings, "OCR_MAX_IMAGE_DIM", 1800)
    height, width = cv2_img.shape[:2]
    if max(height, width) > max_dim:
        scale = max_dim / max(height, width)
        cv2_img = cv2.resize(
            cv2_img, (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
        steps.append(f"resize:{scale:.2f}")

    gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)

    # Mild denoise only if the image looks noisy (high variance); the heavy
    # fastNlMeans filter blurred small-print text, so it is used sparingly.
    denoise = getattr(settings, "OCR_DENOISE", True)
    if denoise:
        variance = float(np.var(gray))
        if variance > 2000:
            gray = cv2.bilateralFilter(gray, 5, 50, 50)
            steps.append("denoise:bilateral")

    variants = _build_variants(gray, steps)

    h2, w2 = gray.shape[:2]
    return PreprocessedImage(
        cv2_image=cv2_img,
        grayscale=gray,
        width=w2,
        height=h2,
        steps_applied=steps,
        variants=variants,
        original_bytes=data,
    )
