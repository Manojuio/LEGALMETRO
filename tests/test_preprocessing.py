"""Tests for the Phase 3 baseline preprocessing (image/preprocessing.py).

Verifies the modular pipeline: decode (+EXIF), resize within max dimension,
grayscale output, denoise/CLAHE/deskew/threshold behaviour and gating, and
— critically — that the original image is never modified and OCR coordinates
stay mappable back to it. No OCR, no DB.
"""

import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageOps

from app.services.image import preprocessing
from app.services.image.preprocessing import (
    THRESHOLD_ADAPTIVE,
    THRESHOLD_OTSU,
    PreprocessedImage,
    preprocess,
    preprocess_bytes,
)
from app.services.image.validator import IMAGE_DECODE_FAILED, ImageValidationError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _tea() -> np.ndarray:
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        return preprocessing.decode(fh.read())


def _label_bgr(height=1200, width=900):
    """Sharp white card with dark rows, as a BGR frame."""
    gray = np.full((height, width), 255, dtype=np.uint8)
    for y in range(80, height - 40, 90):
        cv2.rectangle(gray, (60, y), (width - 60, y + 22), 0, -1)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


# ---------- decode ----------

def test_decode_returns_bgr_tea():
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        arr = preprocessing.decode(fh.read())
    assert arr.ndim == 3
    assert arr.shape[2] == 3
    assert arr.shape[:2] == (1200, 900)


def test_decode_applies_exif_orientation():
    # Camera-style JPEG with Orientation=6 (rotate 90 CW to display).
    buf = io.BytesIO()
    raw = Image.new("RGB", (100, 200), "white")
    exif = Image.Exif()
    exif[274] = 6  # Orientation tag
    raw.save(buf, format="JPEG", exif=exif)
    # Expected display size comes from transposing the SAVED file's exif.
    reopened = Image.open(io.BytesIO(buf.getvalue()))
    expected = ImageOps.exif_transpose(reopened).size
    assert expected == (200, 100), "fixture sanity: orientation tag must transpose"

    arr = preprocessing.decode(buf.getvalue())
    assert (arr.shape[1], arr.shape[0]) == expected


def test_decode_corrupt_raises_validation_error():
    with pytest.raises(ImageValidationError) as e:
        preprocessing.decode(b"definitely not an image")
    assert e.value.code == IMAGE_DECODE_FAILED


# ---------- baseline pipeline ----------

def test_preprocess_baseline_shapes_and_steps():
    pre = preprocess(_tea())
    assert isinstance(pre, PreprocessedImage)
    # processed is grayscale; original is the untouched BGR frame.
    assert pre.processed.ndim == 2
    assert pre.original.ndim == 3
    assert pre.width == 750
    assert pre.height == 1000
    assert pre.original_width == 900
    assert pre.original_height == 1200
    assert "grayscale" in pre.steps_applied
    # Defaults: deskew/CLAHE/threshold are OFF and must not appear.
    assert not any("clahe" in s for s in pre.steps_applied)
    assert not any("deskew" in s for s in pre.steps_applied)
    assert not any("threshold" in s for s in pre.steps_applied)


def test_preprocess_bytes_roundtrip():
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        pre = preprocess_bytes(fh.read())
    assert pre.processed.shape[:2] == (1000, 750)


def test_preprocess_rejects_non_bgr():
    with pytest.raises(ValueError):
        preprocess(np.zeros((100, 100), dtype=np.uint8))  # grayscale, not BGR


# ---------- original preservation + coordinate mapping ----------

def test_original_image_never_modified():
    img = _label_bgr()
    before = img.copy()
    pre = preprocess(img, {"denoise": False})
    # Caller's array untouched and identical to the preserved original.
    assert np.array_equal(img, before)
    assert np.array_equal(pre.original, before)
    # Processed must be a distinct array (fresh copy semantics).
    assert pre.processed is not pre.original


def test_bbox_mapping_back_to_original_after_resize():
    # 2400x1800 original -> forced max_dim 1200 -> processed (900, 1200, ...)
    img = _label_bgr(height=1800, width=2400)
    pre = preprocess(img, {"max_dim": 1200, "denoise": False})
    assert pre.original_width == 2400
    assert pre.original_height == 1800
    assert (pre.width, pre.height) == (1200, 900)
    # A box spanning the full processed image must map back to the original.
    mapped = pre.bbox_to_original([0, 0, pre.width, pre.height])
    assert mapped == [0, 0, 2400, 1800]
    # scale factors are > 1 when we downscaled.
    assert pre.scale_x == pytest.approx(2.0)
    assert pre.scale_y == pytest.approx(2.0)


# ---------- resize ----------

def test_resize_respects_max_dimension():
    img = _label_bgr(height=1800, width=2400)  # longest edge 2400
    pre = preprocess(img, {"max_dim": 1000, "denoise": False})
    assert max(pre.width, pre.height) <= 1000
    # 2400 -> 1000 keeps aspect ratio: width 1000, height 750.
    assert (pre.width, pre.height) == (1000, 750)
    assert any(s.startswith("resize:") for s in pre.steps_applied)
    # No resize needed for an image under the cap.
    pre2 = preprocess(_tea(), {"max_dim": 5000, "denoise": False})
    assert not any(s.startswith("resize:") for s in pre2.steps_applied)


# ---------- denoise ----------

def test_denoise_can_be_disabled():
    pre = preprocess(_tea(), {"denoise": False})
    assert not any(s.startswith("denoise:") for s in pre.steps_applied)


def test_denoise_triggered_on_noisy_image():
    # Uniform gray + heavy Gaussian noise -> high variance, bilateral applies.
    rng = np.random.default_rng(7)
    noisy = np.clip(128 + rng.normal(0, 60, (400, 400)), 0, 255).astype(np.uint8)
    bgr = cv2.cvtColor(noisy, cv2.COLOR_GRAY2BGR)
    pre = preprocess(bgr, {"denoise": True})
    assert any(s.startswith("denoise:") for s in pre.steps_applied)
    # Denoising must reduce the pixel variance.
    var_in = float(np.var(noisy))
    var_out = float(np.var(pre.processed))
    assert var_out < var_in


# ---------- CLAHE ----------

def test_clahe_only_when_enabled_or_required():
    # Sharp, high-contrast label with the flag OFF -> no CLAHE.
    pre = preprocess(_label_bgr(), {"clahe": False})
    assert not any("clahe" in s for s in pre.steps_applied)

    # Same label with the flag ON -> CLAHE applies.
    pre_on = preprocess(_label_bgr(), {"clahe": True})
    assert any(s.startswith("clahe:") for s in pre_on.steps_applied)

    # Washed-out image (low contrast) triggers auto-CLAHE even with flag OFF.
    low = np.full((400, 400), 160, dtype=np.uint8)
    cv2.rectangle(low, (40, 40), (360, 90), 205, -1)  # weak separation
    bgr = cv2.cvtColor(low, cv2.COLOR_GRAY2BGR)
    pre_auto = preprocess(bgr, {"clahe": False, "denoise": False})
    assert any(s == "clahe:auto" for s in pre_auto.steps_applied)
    # Output must differ from input (enhancement actually ran) and stay gray.
    assert not np.array_equal(pre_auto.processed, low)
    assert pre_auto.processed.ndim == 2


# ---------- deskew ----------

def _text_line_image(angle_deg: float):
    """Grayscale image with one long horizontal text band, rotated."""
    img = np.full((400, 800), 255, dtype=np.uint8)
    for y in range(150, 400, 25):
        cv2.rectangle(img, (40, y), (760, y + 14), 0, -1)
    if angle_deg:
        h, w = img.shape[:2]
        rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
        img = cv2.warpAffine(img, rot, (w, h), borderMode=cv2.BORDER_REPLICATE)
    return img


def test_estimate_skew_angle_detects_rotation():
    assert preprocessing.estimate_skew_angle(_text_line_image(0.0)) == pytest.approx(0.0, abs=1.5)
    angle = preprocessing.estimate_skew_angle(_text_line_image(6.0))
    # Sign convention depends on the rotation direction; magnitude is what
    # matters (deskew rotates by the measured angle, whatever its sign).
    assert abs(abs(angle) - 6.0) < 2.0


def test_deskew_gated_by_option():
    bgr = cv2.cvtColor(_text_line_image(6.0), cv2.COLOR_GRAY2BGR)

    # OFF (default): image untouched, no deskew step.
    pre_off = preprocess(bgr, {"denoise": False, "deskew": False})
    assert not any("deskew" in s for s in pre_off.steps_applied)

    # ON: skew corrected to near zero and step recorded.
    pre_on = preprocess(bgr, {"denoise": False, "deskew": True})
    assert any(s.startswith("deskew:") for s in pre_on.steps_applied)
    residual = preprocessing.estimate_skew_angle(pre_on.processed)
    assert abs(residual) < 1.0


def test_deskew_noop_when_already_straight():
    bgr = cv2.cvtColor(_text_line_image(0.0), cv2.COLOR_GRAY2BGR)
    pre = preprocess(bgr, {"denoise": False, "deskew": True})
    assert not any("deskew" in s for s in pre.steps_applied)


# ---------- threshold ----------

def test_threshold_gated_by_option():
    bgr = _label_bgr()
    # OFF (default): not binarized.
    pre_off = preprocess(bgr, {"denoise": False})
    assert not any("threshold" in s for s in pre_off.steps_applied)

    # Otsu: output is strictly binary {0, 255}.
    pre_otsu = preprocess(bgr, {"denoise": False, "threshold": THRESHOLD_OTSU})
    assert any(s == "threshold:otsu" for s in pre_otsu.steps_applied)
    unique = set(np.unique(pre_otsu.processed).tolist())
    assert unique <= {0, 255}

    # Adaptive: also binarized.
    pre_ada = preprocess(bgr, {"denoise": False, "threshold": THRESHOLD_ADAPTIVE})
    assert any(s == "threshold:adaptive" for s in pre_ada.steps_applied)


def test_options_are_recorded():
    pre = preprocess(_tea(), {"denoise": False, "deskew": False})
    assert pre.options_used["denoise"] is False
    assert set(pre.options_used) == {"max_dim", "denoise", "clahe", "deskew", "threshold"}
