"""Image validation — Phase 1 of the OCR engine rebuild.

Single source of truth for validating an image before it may enter the
OCR pipeline. Owns, in order:

1. payload presence (empty input)
2. file size within the configured limit
3. decodability (full Pillow decode — corruption surfaces here)
4. format allow-list
5. dimension sanity (non-zero, above configured minimums)

Corrupted or invalid images are rejected here with stable error codes and
human-readable messages. Nothing reaches OCR unvalidated.

This module performs NO OCR, NO preprocessing, and NO compliance logic.
It is pure validation; the metadata dict it returns is evidence input.

Error codes (stable across the engine — see docs/OCR_ENGINE.md):
    INVALID_IMAGE        unsupported format / empty payload
    IMAGE_DECODE_FAILED  bytes are not a decodable image (corrupt)
    IMAGE_TOO_LARGE      exceeds MAX_UPLOAD_SIZE_MB
    IMAGE_TOO_SMALL      below OCR_MIN_IMAGE_WIDTH/HEIGHT
    IMAGE_NOT_FOUND      path-based entry: file missing/unreadable
"""

import io
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

# Stable error codes.
INVALID_IMAGE = "INVALID_IMAGE"
IMAGE_DECODE_FAILED = "IMAGE_DECODE_FAILED"
IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
IMAGE_TOO_SMALL = "IMAGE_TOO_SMALL"
IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"


class ImageValidationError(Exception):
    """Raised when an image fails validation.

    Carries a stable ``code`` (one of the module constants) plus a
    human-readable ``message``. For migration compatibility the message may
    be passed positionally as the only argument; the code then defaults to
    INVALID_IMAGE.
    """

    def __init__(self, code_or_message: str, message: str | None = None):
        if message is None:
            message = code_or_message
            code = INVALID_IMAGE
        else:
            code = code_or_message
        super().__init__(message)
        self.code = code
        self.message = message


def validate_image_bytes(data: bytes, filename: str | None = None) -> dict:
    """Validate raw image bytes; return metadata on success.

    Raises ImageValidationError with a stable code on any failure.
    """
    settings = get_settings()

    if not data:
        raise ImageValidationError(INVALID_IMAGE, "Uploaded file is empty")

    # 1. Size limit first — never decode an oversized payload.
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise ImageValidationError(
            IMAGE_TOO_LARGE,
            f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    # 2. Full Pillow decode so corruption/truncation surfaces here.
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # UnidentifiedImageError, OSError, ...
        raise ImageValidationError(
            IMAGE_DECODE_FAILED, f"Cannot read image: {exc}"
        ) from exc

    # 3. Format allow-list (based on the decoded container format).
    mime_type = img.format and ("image/" + img.format.lower()) or ""
    if mime_type not in settings.ALLOWED_IMAGE_TYPES:
        allowed = ", ".join(settings.ALLOWED_IMAGE_TYPES)
        raise ImageValidationError(
            INVALID_IMAGE,
            f"Unsupported image type '{mime_type}'. Allowed: {allowed}",
        )

    # 4. Dimension checks.
    width, height = img.size
    if width < 1 or height < 1:
        raise ImageValidationError(
            INVALID_IMAGE, f"Image has invalid dimensions: {width}x{height}"
        )
    if width < settings.OCR_MIN_IMAGE_WIDTH or height < settings.OCR_MIN_IMAGE_HEIGHT:
        raise ImageValidationError(
            IMAGE_TOO_SMALL,
            f"Image too small: {width}x{height} — minimum "
            f"{settings.OCR_MIN_IMAGE_WIDTH}x{settings.OCR_MIN_IMAGE_HEIGHT}",
        )

    return {
        "width": width,
        "height": height,
        "format": img.format,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "filename": filename or "upload.jpg",
    }


def validate_image_file(path: str | Path) -> dict:
    """Validate an image on disk (used for stored uploads).

    Raises ImageValidationError(IMAGE_NOT_FOUND) when the file is missing or
    unreadable; otherwise behaves exactly like validate_image_bytes.
    """
    p = Path(path)
    if not p.exists():
        raise ImageValidationError(IMAGE_NOT_FOUND, f"Image file not found: {path}")
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise ImageValidationError(
            IMAGE_NOT_FOUND, f"Cannot read image file {path}: {exc}"
        ) from exc
    return validate_image_bytes(data, p.name)
