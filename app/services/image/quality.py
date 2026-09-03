"""Image quality assessment — Phase 2 of the OCR engine rebuild.

Deterministic, OpenCV-only quality metrics for a decoded image. This module
NEVER silently rejects an image: it classifies quality and returns warnings,
and the caller decides what to do.

Metrics (all deterministic, no ML):
- width / height / megapixels          — resolution
- blur_score                          — variance of the Laplacian (higher = sharper)
- brightness_score                    — mean grayscale luminance, 0..1
- contrast_score                      — (P98 - P2) / 255, robust percentile spread, 0..1

Grade mapping (worst metric wins):
    GOOD        no concerns — expected to OCR well
    ACCEPTABLE  minor concerns (warning emitted)
    POOR        degraded but OCR may still be attempted (warning emitted)
    UNUSABLE    effectively blank / no readable structure — OCR not worth it

The OCR pipeline may still execute on POOR images, but must surface the
warning in its result. UNUSABLE implies ``usable == False``.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from app.core.config import get_settings

# Grade constants.
GOOD = "GOOD"
ACCEPTABLE = "ACCEPTABLE"
POOR = "POOR"
UNUSABLE = "UNUSABLE"

# Severity order: higher index = worse.
_GRADE_ORDER = {GOOD: 0, ACCEPTABLE: 1, POOR: 2, UNUSABLE: 3}

# Contrast bands (percentile spread / 255). Not config-gated because they are
# scale-free quality yardsticks; calibrate here with real photos in Phase 15.
# A clean ink-on-paper label is near 1.0; < 0.25 is washed out for OCR.
_CONTRAST_GOOD = 0.5
_CONTRAST_ACCEPTABLE = 0.25
_CONTRAST_POOR = 0.12

# Hard floors below which an image is treated as near-blank (used only when
# the config brightness band does not already classify it).
_DARK_UNUSABLE = 0.05
_BRIGHT_UNUSABLE = 0.97


@dataclass
class ImageQuality:
    """Deterministic quality assessment of one image."""

    grade: str
    width: int
    height: int
    blur_score: float
    brightness_score: float
    contrast_score: float
    warnings: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        """UNUSABLE images should not be sent to OCR."""
        return self.grade != UNUSABLE

    @property
    def megapixels(self) -> float:
        return round(self.width * self.height / 1_000_000, 3)

    def to_dict(self) -> dict:
        """Serializable evidence dict (see docs/OCR_ENGINE.md)."""
        return {
            "usable": self.usable,
            "grade": self.grade,
            "width": self.width,
            "height": self.height,
            "megapixels": self.megapixels,
            "blur_score": round(self.blur_score, 2),
            "brightness_score": round(self.brightness_score, 2),
            "contrast_score": round(self.contrast_score, 2),
            "warnings": list(self.warnings),
        }


def _to_gray(image: np.ndarray) -> np.ndarray:
    """Accept BGR (3-channel) or grayscale (2-channel) input."""
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.ndim == 2:
        return image
    raise ValueError(f"Unsupported image shape: {image.shape}")


def _worst(grade: str, other: str) -> str:
    return grade if _GRADE_ORDER[grade] >= _GRADE_ORDER[other] else other


def assess(image: np.ndarray) -> ImageQuality:
    """Assess the quality of a decoded image (BGR or grayscale ndarray)."""
    if image is None or image.size == 0:
        raise ValueError("Cannot assess an empty image")
    settings = get_settings()

    gray = _to_gray(image)
    height, width = gray.shape[:2]
    warnings: list[str] = []
    grade = GOOD

    # --- Resolution / dimensions -------------------------------------------
    if width < settings.OCR_MIN_IMAGE_WIDTH or height < settings.OCR_MIN_IMAGE_HEIGHT:
        warnings.append(
            f"Image below recommended minimum resolution "
            f"({width}x{height} < {settings.OCR_MIN_IMAGE_WIDTH}x"
            f"{settings.OCR_MIN_IMAGE_HEIGHT})"
        )
        grade = _worst(grade, POOR)

    # --- Blur / sharpness: variance of Laplacian ----------------------------
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_thr = settings.OCR_BLUR_THRESHOLD
    if blur_score < blur_thr:
        if blur_score < blur_thr * 0.25:
            warnings.append(f"Image severely blurred (blur_score={blur_score:.1f})")
            grade = _worst(grade, UNUSABLE)
        elif blur_score < blur_thr * 0.5:
            warnings.append(f"Image blurred (blur_score={blur_score:.1f})")
            grade = _worst(grade, POOR)
        else:
            warnings.append(f"Low sharpness (blur_score={blur_score:.1f})")
            grade = _worst(grade, ACCEPTABLE)

    # --- Brightness: mean grayscale luminance -------------------------------
    brightness_score = float(np.mean(gray)) / 255.0
    lo = settings.OCR_BRIGHTNESS_LOW
    hi = settings.OCR_BRIGHTNESS_HIGH
    if brightness_score < lo:
        if brightness_score < _DARK_UNUSABLE:
            warnings.append(
                f"Image too dark (brightness={brightness_score:.2f})"
            )
            grade = _worst(grade, UNUSABLE)
        elif brightness_score < lo * 0.5:
            warnings.append(
                f"Image very dark (brightness={brightness_score:.2f})"
            )
            grade = _worst(grade, POOR)
        else:
            warnings.append(f"Image darker than ideal (brightness={brightness_score:.2f})")
            grade = _worst(grade, ACCEPTABLE)
    elif brightness_score > hi:
        if brightness_score > _BRIGHT_UNUSABLE:
            warnings.append(
                f"Image too bright (brightness={brightness_score:.2f})"
            )
            grade = _worst(grade, UNUSABLE)
        elif brightness_score > hi + (1.0 - hi) * 0.5:
            warnings.append(
                f"Image very bright (brightness={brightness_score:.2f})"
            )
            grade = _worst(grade, POOR)
        else:
            warnings.append(
                f"Image brighter than ideal (brightness={brightness_score:.2f})"
            )
            grade = _worst(grade, ACCEPTABLE)

    # --- Contrast: robust percentile spread ---------------------------------
    p2, p98 = np.percentile(gray, (2, 98))
    contrast_score = float(p98 - p2) / 255.0
    if contrast_score < _CONTRAST_POOR:
        warnings.append(
            f"Image has almost no contrast (contrast={contrast_score:.2f})"
        )
        grade = _worst(grade, UNUSABLE)
    elif contrast_score < _CONTRAST_ACCEPTABLE:
        warnings.append(
            f"Low contrast (contrast={contrast_score:.2f})"
        )
        grade = _worst(grade, POOR)
    elif contrast_score < _CONTRAST_GOOD:
        warnings.append(
            f"Moderate contrast (contrast={contrast_score:.2f})"
        )
        grade = _worst(grade, ACCEPTABLE)

    return ImageQuality(
        grade=grade,
        width=width,
        height=height,
        blur_score=blur_score,
        brightness_score=brightness_score,
        contrast_score=contrast_score,
        warnings=warnings,
    )


def assess_bytes(data: bytes) -> ImageQuality:
    """Decode raw image bytes (Pillow + EXIF) and assess quality.

    Convenience wrapper for callers holding bytes instead of an ndarray.
    Decoding is preprocessing's job (image/preprocessing.py).
    """
    from app.services.image.preprocessing import decode

    return assess(decode(data))
