"""Content moderation database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class ModerationQueue(Base, UUIDMixin, TimestampMixin):
    """Item in the moderation queue."""

    __tablename__ = "moderation_queue"

    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # post, comment, message, media
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    pipeline: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # pre_publish, post_publish
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected, escalated
    risk_scores: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    age_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class ModerationDecision(Base, UUIDMixin, TimestampMixin):
    """Decision made on a moderation queue item."""

    __tablename__ = "moderation_decisions"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("moderation_queue.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    moderator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )  # nullable for automated decisions
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # approve, reject, escalate
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class ContentReport(Base, UUIDMixin, TimestampMixin):
    """User-submitted content report."""

    __tablename__ = "content_reports"

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, reviewed, dismissed


class MediaAsset(Base, UUIDMixin, TimestampMixin):
    """Media asset stored in Cloudflare R2/Images/Stream."""

    __tablename__ = "media_assets"

    cloudflare_r2_key: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
    )
    cloudflare_image_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    cloudflare_stream_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    media_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # image, video
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    variants: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    content_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
