"""Tests for the Phase 2 image quality assessment (image/quality.py).

Synthesizes images with OpenCV so each metric can be tested in isolation:
sharp label, blurred, dark, overexposed, low-contrast, blank, tiny. Pure
unit tests — no OCR, no DB.
"""

import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.core.config import get_settings
from app.services.image import quality
from app.services.image.quality import ACCEPTABLE, GOOD, POOR, UNUSABLE, ImageQuality

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _label_image(size=(900, 1200), text_value=0, background=255):
    """White card with dark 'text' rows (high-frequency edges -> sharp)."""
    img = np.full((size[1], size[0]), background, dtype=np.uint8)
    for y in range(80, size[1] - 80, 90):
        cv2.rectangle(img, (60, y), (size[0] - 60, y + 22), text_value, -1)
    return img


# ---------- GOOD / baseline ----------

def test_sharp_high_contrast_label_is_good():
    img = _label_image()
    q = quality.assess(img)
    assert q.grade == GOOD
    assert q.usable is True
    assert q.warnings == []
    assert q.width == 900
    assert q.height == 1200
    assert q.megapixels == pytest.approx(1.08, abs=0.01)
    # Sharp text on white: strong blur metric, near-max contrast.
    assert q.blur_score >= get_settings().OCR_BLUR_THRESHOLD
    assert q.brightness_score > 0.5
    assert q.contrast_score > 0.8


def test_to_dict_shape():
    q = quality.assess(_label_image())
    d = q.to_dict()
    for key in (
        "usable", "grade", "width", "height", "megapixels",
        "blur_score", "brightness_score", "contrast_score", "warnings",
    ):
        assert key in d
    assert d["grade"] == GOOD


def test_assess_bytes_accepts_real_image_bytes():
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        data = fh.read()
    q = quality.assess_bytes(data)
    assert isinstance(q, ImageQuality)
    assert q.width == 900
    assert q.height == 1200
    assert 0.0 <= q.brightness_score <= 1.0
    assert 0.0 <= q.contrast_score <= 1.0


def test_assess_bgr_color_input():
    color = cv2.cvtColor(_label_image(), cv2.COLOR_GRAY2BGR)
    q = quality.assess(color)
    assert q.grade == GOOD


def test_assess_empty_raises():
    with pytest.raises(ValueError):
        quality.assess(np.zeros((0, 0), dtype=np.uint8))


# ---------- Blur ----------

def test_blurred_image_flagged():
    img = cv2.GaussianBlur(_label_image(), (41, 41), 0)
    q = quality.assess(img)
    assert q.grade != GOOD
    assert q.blur_score < get_settings().OCR_BLUR_THRESHOLD
    assert any("blur" in w.lower() or "sharp" in w.lower() for w in q.warnings)


# ---------- Brightness ----------

def test_dark_image_flagged():
    img = np.clip(_label_image() * 0.06, 0, 255).astype(np.uint8)
    q = quality.assess(img)
    assert q.brightness_score < get_settings().OCR_BRIGHTNESS_LOW
    assert q.grade in (POOR, UNUSABLE)
    assert any("dark" in w.lower() for w in q.warnings)


def test_overexposed_image_flagged():
    img = np.clip(_label_image().astype(np.int16) + 200, 0, 255).astype(np.uint8)
    q = quality.assess(img)
    assert q.brightness_score > get_settings().OCR_BRIGHTNESS_HIGH
    assert q.grade in (ACCEPTABLE, POOR, UNUSABLE)
    assert q.grade != GOOD


# ---------- Contrast ----------

def test_low_contrast_image_flagged():
    # bg 160 / text 205: ~18% percentile spread -> washed out for OCR.
    img = _label_image(text_value=205, background=160)
    q = quality.assess(img)
    assert q.grade in (POOR, UNUSABLE)
    assert any("contrast" in w.lower() for w in q.warnings)


def test_blank_uniform_image_unusable():
    img = np.full((900, 1200), 128, dtype=np.uint8)
    q = quality.assess(img)
    assert q.grade == UNUSABLE
    assert q.usable is False
    assert q.warnings  # explains why


# ---------- Resolution ----------

def test_tiny_image_downgraded_with_warning():
    # Sharp, high-contrast content on a tiny canvas -> only the resolution
    # check can be responsible for the downgrade.
    img = np.full((80, 60), 255, dtype=np.uint8)
    cv2.rectangle(img, (5, 10), (55, 30), 0, -1)
    q = quality.assess(img)
    assert q.grade == POOR
    assert q.usable is True  # never silently rejected
    assert any("resolution" in w.lower() for w in q.warnings)
    assert q.width == 60
    assert q.height == 80


# ---------- Config-driven boundaries ----------

def test_boundaries_follow_config():
    s = get_settings()
    # Mid-gray, uniform: contrast forces UNUSABLE regardless of brightness.
    q = quality.assess(np.full((400, 400), 128, dtype=np.uint8))
    assert q.grade == UNUSABLE
    # Direct config sanity: defaults must be consistent for the tests above.
    assert s.OCR_BLUR_THRESHOLD > 0
    assert 0 < s.OCR_BRIGHTNESS_LOW < s.OCR_BRIGHTNESS_HIGH < 1
