"""Tests for image upload, preprocessing, and OCR services.

Uses synthetic fixture images. These tests verify the pipeline runs and
produces structured evidence. They do NOT assert legal compliance.
"""

from pathlib import Path

import pytest

from app.services import image_service, ocr_service

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> bytes:
    with open(FIXTURES / name, "rb") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def tea_bytes():
    return _load("valid_tea.jpg")


# ---------- Image validation ----------

def test_validate_valid_image(tea_bytes):
    meta = image_service.validate_image_bytes(tea_bytes, "valid_tea.jpg")
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert meta["mime_type"].startswith("image/")
    assert "size_bytes" in meta


def test_validate_rejects_empty():
    with pytest.raises(image_service.ImageValidationError):
        image_service.validate_image_bytes(b"")


def test_validate_rejects_non_image():
    with pytest.raises(image_service.ImageValidationError):
        image_service.validate_image_bytes(b"this is not an image at all")


def test_validate_rejects_oversized():
    # Create a fake large payload that exceeds the size limit. We can't easily
    # shrink the pydantic setting, so we verify the SIZE check by directly
    # invoking the size-limit logic path with a payload larger than the allowed
    # maximum (default 10MB) plus a valid tiny image header.
    from app.core.config import get_settings
    settings = get_settings()
    # Build a payload larger than the limit
    big = bytearray(1024)  # start small
    # If default limit is 10MB, generate >10MB without holding in memory
    limit_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    # use a valid JPEG header so decode would otherwise pass
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (5, 5), "white").save(buf, format="JPEG")
    header = buf.getvalue()
    filler_size = limit_bytes + 1
    fake = header + b"\xff" * filler_size
    with pytest.raises(image_service.ImageValidationError) as e:
        image_service.validate_image_bytes(fake)
    assert "exceeds" in str(e.value).lower()


# ---------- Preprocessing ----------

def test_preprocess_returns_dimensions(tea_bytes):
    pre = image_service.preprocess(tea_bytes)
    assert pre.width > 0
    assert pre.height > 0
    assert pre.grayscale.ndim == 2
    assert pre.cv2_image.ndim == 3
    assert pre.steps_applied  # at least one preprocessing step recorded


def test_preprocess_exif_transpose_png():
    # Create a small PNG, decode without crash
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (50, 60), "white").save(buf, format="PNG")
    pre = image_service.preprocess(buf.getvalue())
    assert pre.width == 50
    assert pre.height == 60


# ---------- OCR run ----------

def test_run_ocr_returns_blocks_and_confidence(tea_bytes):
    pre = image_service.preprocess(tea_bytes)
    result = ocr_service.run_ocr(pre.grayscale, pre.steps_applied)
    assert result.engine == "easyocr"
    assert result.processing_time_ms >= 0
    assert isinstance(result.raw_text, str)
    # We cannot assert high accuracy on synthetic images, only structure.
    assert result.confidence_score >= 0.0
    assert result.confidence_score <= 1.0


def test_run_ocr_block_shape(tea_bytes):
    pre = image_service.preprocess(tea_bytes)
    result = ocr_service.run_ocr(pre.grayscale, pre.steps_applied)
    for block in result.blocks:
        assert len(block.bbox) == 4  # x, y, w, h
        assert block.bbox[2] >= 0  # width non-negative
        assert block.bbox[3] >= 0  # height non-negative
        assert isinstance(block.confidence, float)


def test_normalize_bbox():
    points = [[10, 20], [110, 20], [110, 60], [10, 60]]
    bbox = ocr_service.normalize_bbox(points)
    assert bbox == [10, 20, 100, 40]


def test_normalize_bbox_empty():
    assert ocr_service.normalize_bbox([]) == [0, 0, 0, 0]
