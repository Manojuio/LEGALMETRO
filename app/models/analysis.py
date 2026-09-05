"""Analysis, ProductImage, OCRResult, and ExtractedField models.

An Analysis is the central entity — it owns images, OCR results,
extracted fields, and rule results.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisOverallStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class ImagePosition(str, enum.Enum):
    FRONT = "FRONT"
    BACK = "BACK"
    SIDE = "SIDE"
    OTHER = "OTHER"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id"), nullable=True
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.PENDING,
    )
    overall_status: Mapped[AnalysisOverallStatus | None] = mapped_column(
        Enum(AnalysisOverallStatus, name="analysis_overall_status"),
        nullable=True,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="analyses")
    product = relationship("Product", back_populates="analyses")
    images = relationship("ProductImage", back_populates="analysis", cascade="all, delete-orphan")
    ocr_results = relationship("OCRResult", back_populates="analysis", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="analysis", cascade="all, delete-orphan")
    rule_results = relationship("RuleResult", back_populates="analysis", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="analysis")
    reports = relationship("Report", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<Analysis {self.id} status={self.status}>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_position: Mapped[ImagePosition] = mapped_column(
        Enum(ImagePosition, name="image_position"), nullable=False
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    analysis = relationship("Analysis", back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage {self.filename} pos={self.image_position}>"


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id"), nullable=False
    )
    image_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_images.id"), nullable=False
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_blocks: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_engine: Mapped[str] = mapped_column(String(50), default="easyocr")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    analysis = relationship("Analysis", back_populates="ocr_results")
    image = relationship("ProductImage")

    def __repr__(self) -> str:
        return f"<OCRResult analysis={self.analysis_id}>"


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_image_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_images.id"), nullable=True
    )
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    analysis = relationship("Analysis", back_populates="extracted_fields")
    source_image = relationship("ProductImage")

    def __repr__(self) -> str:
        return f"<ExtractedField {self.field_name}={self.field_value}>"
