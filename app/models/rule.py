"""Rule, RuleResult, and RuleResultEvidence models.

Rules are loaded from rules/rules.json.
RuleResults are produced by the compliance engine per analysis.
Evidence links results back to OCR blocks for auditability.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RuleStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    rule_number: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    input_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    automation_level: Mapped[str] = mapped_column(String(50), nullable=False)
    applicable_to: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    package_types: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_required: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    rule_results = relationship("RuleResult", back_populates="rule")

    def __repr__(self) -> str:
        return f"<Rule {self.id} title={self.title}>"


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("rules.id"), nullable=False
    )
    status: Mapped[RuleStatus] = mapped_column(
        Enum(RuleStatus, name="rule_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validator_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    analysis = relationship("Analysis", back_populates="rule_results")
    rule = relationship("Rule", back_populates="rule_results")
    evidence = relationship(
        "RuleResultEvidence", back_populates="rule_result", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RuleResult rule={self.rule_id} status={self.status}>"


class RuleResultEvidence(Base):
    __tablename__ = "rule_result_evidence"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rule_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rule_results.id"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_image_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_images.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    rule_result = relationship("RuleResult", back_populates="evidence")
    source_image = relationship("ProductImage")

    def __repr__(self) -> str:
        return f"<RuleResultEvidence type={self.evidence_type}>"
