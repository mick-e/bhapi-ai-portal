"""UK AADC compliance database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class AadcAssessment(Base, UUIDMixin, TimestampMixin):
    """AADC gap analysis assessment record.

    Stores the result of evaluating all 15 AADC standards for a group,
    including per-standard compliance status and recommendations.
    """

    __tablename__ = "aadc_assessments"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(
        nullable=False, default=1
    )
    standards: Mapped[dict | list] = mapped_column(
        JSONType, nullable=False
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assessor: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    overall_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="non_compliant"
    )


class PrivacyDefault(Base, UUIDMixin, TimestampMixin):
    """Privacy-by-default settings record per user and age tier.

    Tracks the maximum-privacy default settings applied to child accounts
    as required by AADC Standard 14.
    """

    __tablename__ = "aadc_privacy_defaults"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    age_tier: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    settings: Mapped[dict] = mapped_column(
        JSONType, nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        String(200), nullable=False, default="system"
    )
