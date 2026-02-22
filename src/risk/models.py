"""Risk & safety engine database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class RiskEvent(Base, UUIDMixin, TimestampMixin):
    """A detected risk event from the safety pipeline."""

    __tablename__ = "risk_events"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )
    capture_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture_events.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # critical, high, medium, low
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    content_excerpts: Mapped[list["ContentExcerpt"]] = relationship(
        back_populates="risk_event", lazy="selectin"
    )


class RiskConfig(Base, UUIDMixin):
    """Per-group risk category configuration."""

    __tablename__ = "risk_configs"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sensitivity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_keywords: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    __table_args__ = (
        # Unique constraint: one config per group per category
        {"comment": "Per-group risk category sensitivity configuration"},
    )


class ContentExcerpt(Base, UUIDMixin):
    """Encrypted content excerpt linked to a risk event.

    Content is encrypted at rest and has a mandatory expiry for data minimisation.
    """

    __tablename__ = "content_excerpts"

    risk_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_events.id"), nullable=False, index=True
    )
    encrypted_content: Mapped[str] = mapped_column(String(4096), nullable=False)
    encryption_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    risk_event: Mapped["RiskEvent"] = relationship(back_populates="content_excerpts")
