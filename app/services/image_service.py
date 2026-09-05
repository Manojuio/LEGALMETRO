"""Image validation, preprocessing, metadata extraction, and Cloudinary storage.

This service owns ALL image handling that is NOT OCR itself:
- validate uploaded bytes
- read and decode an image with OpenCV
- preprocess an image to improve OCR accuracy
- extract metadata
- upload images to Cloudinary
- retrieve stored images as bytes

OCR must NOT happen here.
"""

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import Request, urlopen

import cloudinary
import cloudinary.uploader
import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.services.image import validator as image_validator
from app.services.image.validator import ImageValidationError


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
    grayscale: np.ndarray
    width: int
    height: int
    steps_applied: list[str]
    variants: list = field(default_factory=list)
    original_bytes: bytes | None = None


def validate_image_bytes(data: bytes, filename: str | None = None) -> dict:
    """Validate raw image bytes.

    Delegates to the single source of truth:
    app/services/image/validator.py
    """
    return image_validator.validate_image_bytes(data, filename)


def _configure_cloudinary() -> None:
    """Configure Cloudinary from application settings."""

    settings = get_settings()

    if not settings.CLOUDINARY_CLOUD_NAME:
        raise RuntimeError("Cloudinary cloud name is not configured")

    if not settings.CLOUDINARY_API_KEY:
        raise RuntimeError("Cloudinary API key is not configured")

    if not settings.CLOUDINARY_API_SECRET:
        raise RuntimeError("Cloudinary API secret is not configured")

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_to_cloudinary(
    analysis_id: str,
    data: bytes,
    position: str,
    original_filename: str,
) -> dict:
    """Upload validated image bytes to Cloudinary.

    Images are organized under:

        legalmetrix/analysis_<analysis_id>/<position>

    The existing application limit and image validation happen BEFORE
    this function is called.
    """

    _configure_cloudinary()

    position = (position or "OTHER").lower()

    ext = os.path.splitext(original_filename or "")[1].lower()
    if not ext:
        ext = ".jpg"

    # Remove the leading dot for Cloudinary format handling.
    image_format = ext.lstrip(".")

    public_id = f"legalmetrix/analysis_{analysis_id}/{position}"

    result = cloudinary.uploader.upload(
        data,
        public_id=public_id,
        resource_type="image",
        overwrite=True,
        format=image_format,
    )

    return {
        "url": result.get("secure_url") or result.get("url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type", "image"),
        "asset_id": result.get("asset_id"),
        "version": result.get("version"),
    }


def save_upload(
    analysis_id: str,
    data: bytes,
    position: str,
    original_filename: str,
) -> tuple[str, dict]:
    """Validate and store one uploaded image in Cloudinary.

    Returns:
        (cloudinary_url, metadata)

    No permanent image file is written to the local uploads directory.
    """

    # IMPORTANT:
    # Validation happens before Cloudinary upload.
    metadata = validate_image_bytes(data, original_filename)

    cloudinary_data = upload_to_cloudinary(
        analysis_id=analysis_id,
        data=data,
        position=position,
        original_filename=original_filename,
    )

    cloudinary_url = cloudinary_data.get("url")

    if not cloudinary_url:
        raise RuntimeError("Cloudinary upload succeeded but no URL was returned")

    # Keep metadata compatible with the existing database layer.
    metadata["saved_path"] = cloudinary_url
    metadata["cloudinary_url"] = cloudinary_url
    metadata["cloudinary_public_id"] = cloudinary_data.get("public_id")
    metadata["cloudinary_asset_id"] = cloudinary_data.get("asset_id")

    position = (position or "OTHER").lower()
    ext = os.path.splitext(original_filename or "")[1].lower() or ".jpg"

    # Keep the application's existing logical filename convention.
    metadata["filename"] = f"{position}{ext}"

    return cloudinary_url, metadata


def download_image_bytes(file_path: str) -> bytes:
    """Return image bytes from either a Cloudinary URL or local path.

    Cloudinary URLs are fetched over HTTPS.
    Local paths are supported for backwards compatibility with old records.
    """

    if not file_path:
        raise ImageValidationError(
            "Image path/URL is empty"
        )

    # New Cloudinary storage
    if file_path.startswith("http://") or file_path.startswith("https://"):
        try:
            request = Request(
                file_path,
                headers={
                    "User-Agent": "LegalMetriX/1.0",
                },
            )

            with urlopen(request, timeout=60) as response:
                data = response.read()

            if not data:
                raise ImageValidationError(
                    "Downloaded image is empty"
                )

            return data

        except Exception as exc:
            raise ImageValidationError(
                f"Cannot download image from Cloudinary: {exc}"
            ) from exc

    # Backwards compatibility for old local images.
    path = Path(file_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise ImageValidationError(
            f"Image file not found: {file_path}"
        )

    try:
        return path.read_bytes()
    except OSError as exc:
        raise ImageValidationError(
            f"Cannot read image file {file_path}: {exc}"
        ) from exc


def decode_to_cv2(data: bytes) -> np.ndarray:
    """Decode image bytes into an OpenCV BGR image."""

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        rgb = np.array(img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    except Exception as exc:
        raise ImageValidationError(
            f"Cannot decode image: {exc}"
        ) from exc


def ensure_upload_dir(analysis_id: str) -> Path:
    """Create and return the upload directory.

    Kept for backwards compatibility.

    New uploads are stored in Cloudinary, not here.
    """

    settings = get_settings()
    base = settings.UPLOAD_DIR
    base.mkdir(parents=True, exist_ok=True)

    analysis_dir = base / f"analysis_{analysis_id}"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    return analysis_dir


def settings_path(relative: Path) -> Path:
    """Resolve a relative path against the project root.

    Kept for backwards compatibility with older callers.
    """

    if relative.is_absolute():
        return relative

    return Path.cwd() / relative


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate text-sheet skew in degrees using Hough line transform."""

    h, w = gray.shape[:2]

    small_h = max(480, int(h * 0.6))

    if small_h >= h:
        small = gray
    else:
        r = small_h / h
        small = cv2.resize(
            gray,
            (int(w * r), small_h),
            interpolation=cv2.INTER_AREA,
        )

    thresh = cv2.threshold(
        small,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )[1]

    lines = cv2.HoughLinesP(
        thresh,
        1,
        np.pi / 180,
        threshold=80,
        minLineLength=max(20, small.shape[1] // 12),
        maxLineGap=8,
    )

    if lines is None or len(lines) == 0:
        return 0.0

    lines = lines.reshape(-1, 4)

    angles = []

    for line in lines:
        x1, y1, x2, y2 = (int(v) for v in line)

        if abs(x2 - x1) < 3:
            continue

        deg = np.degrees(
            np.arctan2(y2 - y1, x2 - x1)
        )

        angles.append(deg)

    if not angles:
        return 0.0

    median_angle = float(np.median(angles))

    if abs(median_angle) < 0.4 or abs(median_angle) > 35:
        return 0.0

    return median_angle


def _deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    h, w = gray.shape[:2]

    center = (w / 2, h / 2)

    rot = cv2.getRotationMatrix2D(
        center,
        angle,
        1.0,
    )

    return cv2.warpAffine(
        gray,
        rot,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _clahe_enhance(
    gray: np.ndarray,
    clip: float = 2.0,
    tile: int = 8,
) -> np.ndarray:
    """Contrast-Limited Adaptive Histogram Equalization."""

    clahe = cv2.createCLAHE(
        clipLimit=clip,
        tileGridSize=(tile, tile),
    )

    return clahe.apply(gray)


def _build_variants(
    gray: np.ndarray,
    steps: list[str],
) -> list:
    """Build OCR image representations."""

    h, w = gray.shape[:2]
    mean_lum = float(np.mean(gray))

    variants = []

    variants.append(
        ImageVariant(
            "gray",
            gray,
            "clean grayscale baseline",
        )
    )
    steps.append("v:gray")

    clahe = _clahe_enhance(gray)

    variants.append(
        ImageVariant(
            "clahe",
            clahe,
            "CLAHE contrast enhanced",
        )
    )
    steps.append("v:clahe")

    if max(h, w) < 1500:
        scale = 2.0 if max(h, w) < 1100 else 1.5

        up = cv2.resize(
            gray,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )

        variants.append(
            ImageVariant(
                "upscaled",
                up,
                f"upscaled {scale:.1f}x",
            )
        )

        steps.append(f"v:upscaled:{scale:.1f}")

    otsu = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU,
    )[1]

    variants.append(
        ImageVariant(
            "otsu",
            otsu,
            "Otsu binarized",
        )
    )

    steps.append("v:otsu")

    angle = _estimate_skew_angle(gray)

    if angle:
        variants.append(
            ImageVariant(
                "deskew",
                _deskew(gray, angle),
                f"deskewed {angle:.1f}deg",
            )
        )

        steps.append(f"v:deskew:{angle:.1f}")

    if mean_lum < 90:
        inv = cv2.bitwise_not(gray)

        variants.append(
            ImageVariant(
                "invert",
                inv,
                "inverted (dark bg)",
            )
        )

        steps.append("v:invert")

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
    """Run the dynamic preprocessing pipeline on image bytes."""

    settings = get_settings()

    cv2_img = decode_to_cv2(data)

    steps: list[str] = []

    max_dim = getattr(
        settings,
        "OCR_MAX_IMAGE_DIM",
        1800,
    )

    height, width = cv2_img.shape[:2]

    if max(height, width) > max_dim:
        scale = max_dim / max(height, width)

        cv2_img = cv2.resize(
            cv2_img,
            (
                int(width * scale),
                int(height * scale),
            ),
            interpolation=cv2.INTER_AREA,
        )

        steps.append(f"resize:{scale:.2f}")

    gray = cv2.cvtColor(
        cv2_img,
        cv2.COLOR_BGR2GRAY,
    )

    denoise = getattr(
        settings,
        "OCR_DENOISE",
        True,
    )

    if denoise:
        variance = float(np.var(gray))

        if variance > 2000:
            gray = cv2.bilateralFilter(
                gray,
                5,
                50,
                50,
            )

            steps.append("denoise:bilateral")

    variants = _build_variants(
        gray,
        steps,
    )

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