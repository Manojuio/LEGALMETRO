"""Pydantic schemas for image upload and OCR responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ImageMetadata(BaseModel):
    """Metadata returned after a successful image upload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    image_position: str
    width: int | None = None
    height: int | None = None


class UploadedImageResponse(BaseModel):
    """Response for a single uploaded image."""

    image: ImageMetadata
    analysis_id: str


class OCRBlockSchema(BaseModel):
    """One normalized OCR text block."""

    text: str
    confidence: float
    bbox: list[int]


class OCRResponse(BaseModel):
    """Response from POST /api/v1/analyses/{id}/ocr."""

    status: str = "completed"
    analysis_id: str
    image_id: str | None = None
    text_blocks: list[OCRBlockSchema]
    raw_text: str
    confidence: float
    processing_time_ms: int
    engine: str
    steps_applied: list[str] = []
