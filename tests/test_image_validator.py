"""Tests for the Phase 1 image validator (app/services/image/validator.py).

Covers the validation contract: valid images pass with metadata; empty,
oversized, corrupt, unsupported, tiny, and missing images are rejected with
clear, stable error codes. No OCR and no DB involved — these run fast.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.image import validator
from app.services.image.validator import (
    IMAGE_DECODE_FAILED,
    IMAGE_NOT_FOUND,
    IMAGE_TOO_LARGE,
    IMAGE_TOO_SMALL,
    INVALID_IMAGE,
    ImageValidationError,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> bytes:
    with open(FIXTURES / name, "rb") as fh:
        return fh.read()


def _png_bytes(size=(400, 400), color="white") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


# ---------- valid images ----------

def test_valid_image_returns_metadata():
    meta = validator.validate_image_bytes(_load("valid_tea.jpg"), "valid_tea.jpg")
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert meta["format"] == "JPEG"
    assert meta["mime_type"] == "image/jpeg"
    assert meta["size_bytes"] > 0
    assert meta["filename"] == "valid_tea.jpg"


def test_valid_png_accepted():
    meta = validator.validate_image_bytes(_png_bytes())
    assert meta["mime_type"] == "image/png"


# ---------- rejected inputs + stable error codes ----------

def test_empty_payload_code():
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(b"")
    assert e.value.code == INVALID_IMAGE
    assert "empty" in e.value.message.lower()


def test_non_image_bytes_decode_failed():
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(b"this is not an image at all")
    assert e.value.code == IMAGE_DECODE_FAILED


def test_corrupted_image_decode_failed():
    # Truncate a valid PNG mid-stream -> full decode must raise.
    png = _png_bytes(size=(300, 300))
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(png[: len(png) // 2])
    assert e.value.code == IMAGE_DECODE_FAILED


def test_oversized_image_too_large():
    from app.core.config import get_settings

    settings = get_settings()
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    payload = _png_bytes() + b"\x00" * (limit + 1)  # valid header, over the limit
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(payload)
    assert e.value.code == IMAGE_TOO_LARGE
    assert "exceeds" in e.value.message.lower()


def test_unsupported_format_invalid_image():
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "red").save(buf, format="GIF")
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(buf.getvalue())
    assert e.value.code == INVALID_IMAGE
    assert "unsupported" in e.value.message.lower()


def test_tiny_image_too_small():
    # Defaults: OCR_MIN_IMAGE_WIDTH/HEIGHT = 200. A 50x60 PNG must be rejected.
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_bytes(_png_bytes(size=(50, 60)))
    assert e.value.code == IMAGE_TOO_SMALL
    assert "too small" in e.value.message.lower()


# ---------- path-based validation (stored uploads) ----------

def test_validate_file_missing_path():
    with pytest.raises(ImageValidationError) as e:
        validator.validate_image_file(FIXTURES / "does_not_exist.jpg")
    assert e.value.code == IMAGE_NOT_FOUND


def test_validate_file_valid_path():
    meta = validator.validate_image_file(FIXTURES / "valid_tea.jpg")
    assert meta["width"] > 0
    assert meta["filename"] == "valid_tea.jpg"


def test_validate_file_corrupt_path():
    png = _png_bytes(size=(300, 300))
    tmp = FIXTURES / "_tmp_corrupt.png"
    try:
        tmp.write_bytes(png[: len(png) // 2])
        with pytest.raises(ImageValidationError) as e:
            validator.validate_image_file(tmp)
        assert e.value.code == IMAGE_DECODE_FAILED
    finally:
        tmp.unlink(missing_ok=True)


# ---------- backward compatibility with image_service ----------

def test_image_service_delegates_to_validator():
    from app.services import image_service

    # Same exception class is re-exported -> callers catching
    # image_service.ImageValidationError keep working.
    assert image_service.ImageValidationError is ImageValidationError

    meta = image_service.validate_image_bytes(_load("valid_tea.jpg"))
    assert meta["mime_type"] == "image/jpeg"

    with pytest.raises(image_service.ImageValidationError) as e:
        image_service.validate_image_bytes(b"")
    assert e.value.code == INVALID_IMAGE
