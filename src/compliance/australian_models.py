"""Australian Online Safety compliance database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class AgeVerificationRecord(Base, UUIDMixin, TimestampMixin):
    """Age verification record for Australian Online Safety Act compliance.

    AU users must verify age before accessing social features.
    verification_data is encrypted via Fernet/KMS.
    """

    __tablename__ = "au_age_verification_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    country_code: Mapped[str] = mapped_column(
        String(2), nullable=False, default="AU"
    )
    method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # yoti, document, self_declaration, parent_verified
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_data: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Encrypted JSON blob


class ESafetyReport(Base, UUIDMixin, TimestampMixin):
    """eSafety Commissioner report tracking with 24-hour SLA.

    Content reported for online safety review must be actioned within 24 hours.
    """

    __tablename__ = "au_esafety_reports"

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # post, comment, message, media
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, actioned, escalated
    action_taken: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )


class CyberbullyingCase(Base, UUIDMixin, TimestampMixin):
    """Structured cyberbullying case with workflow tracking.

    Workflow: detect → document → notify parent → review → action → escalate → resolve
    """

    __tablename__ = "au_cyberbullying_cases"

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    evidence_ids: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # low, medium, high, critical
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )  # open, investigating, closed
    workflow_steps: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )
    resolution: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
