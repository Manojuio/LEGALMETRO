"""User model with role-based access control and zone mapping.

Zones model the administrative/geographic jurisdiction of a Legal Metrology
Officer (LMO). An ADMIN assigns LMOs to a zone; the ADMIN sees the LMOs in
that zone on the dashboard. Zone membership may be shared by multiple LMOs.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    LMO = "LMO"
    MANUFACTURER = "MANUFACTURER"
    RETAILER = "RETAILER"
    CONSUMER = "CONSUMER"


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    users = relationship("User", back_populates="zone")

    def __repr__(self) -> str:
        return f"<Zone {self.name}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    zone_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("zones.id"), nullable=True
    )
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
    zone = relationship("Zone", back_populates="users")
    analyses = relationship("Analysis", back_populates="user")
    inspections = relationship("Inspection", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"
