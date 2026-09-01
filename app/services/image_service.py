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
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import get_settings


class ImageValidationError(Exception):
    """Raised when an uploaded file fails validation."""


@dataclass
class PreprocessedImage:
    """Result of preprocessing one image."""

    cv2_image: np.ndarray
    grayscale: np.ndarray
    width: int
    height: int
    steps_applied: list[str]
    original_bytes: bytes | None = None


def validate_image_bytes(data: bytes, filename: str | None = None) -> dict:
    """Validate raw uploaded bytes.

    Returns metadata dict on success. Raises ImageValidationError on failure.
    Checks, in order:
    1. Non-empty payload
    2. File size limit (from settings)
    3. Decodable by Pillow (integrity / corruption)
    4. Allowed MIME type
    """
    settings = get_settings()

    if not data:
        raise ImageValidationError("Uploaded file is empty")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise ImageValidationError(
            f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
        )

    # Decode with Pillow to verify the image isn't corrupt
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # force full decode so corruption surfaces here
    except Exception as exc:
        raise ImageValidationError(f"Cannot read image: {exc}") from exc

    mime_type = img.format and ("image/" + img.format.lower()) or ""
    if mime_type not in settings.ALLOWED_IMAGE_TYPES:
        allowed = ", ".join(settings.ALLOWED_IMAGE_TYPES)
        raise ImageValidationError(
            f"Unsupported image type '{mime_type}'. Allowed: {allowed}"
        )

    width, height = img.size
    return {
        "width": width,
        "height": height,
        "format": img.format,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "filename": filename or "upload.jpg",
    }


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


def preprocess(data: bytes) -> PreprocessedImage:
    """Run the preprocessing pipeline on an image.

    Steps (each recorded in steps_applied):
    1. Decode with OpenCV (grayscale, EXIF-normalized)
    2. Resize if larger than a max dimension (keeps aspect ratio)
    3. Denoise (fastNlMeansDenoising)
    4. Adaptive thresholding / contrast enhancement
    5. Optionally deskew (skipped for now — limited value for photos)

    Returns a PreprocessedImage with the raw color image plus the
    prepared grayscale image for OCR.
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

    denoise = getattr(settings, "OCR_DENOISE", True)
    if denoise:
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        steps.append("denoise")

    threshold = getattr(settings, "OCR_THRESHOLD", True)
    if threshold:
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
        )
        steps.append("adaptive_threshold")

    h2, w2 = gray.shape[:2]
    return PreprocessedImage(
        cv2_image=cv2_img,
        grayscale=gray,
        width=w2,
        height=h2,
        steps_applied=steps,
        original_bytes=data,
    )
