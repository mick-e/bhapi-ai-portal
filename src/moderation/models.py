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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, under_review, action_taken, dismissed


class ModerationAppeal(Base, UUIDMixin, TimestampMixin):
    """User appeal of a moderation decision."""

    __tablename__ = "moderation_appeals"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("moderation_queue.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    appellant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, accepted, denied
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


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


class ModeratorAssignment(Base, UUIDMixin, TimestampMixin):
    """Assignment of a moderator to a queue item."""

    __tablename__ = "moderator_assignments"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("moderation_queue.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="assigned",
    )  # assigned, completed, reassigned
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class SLAMetric(Base, UUIDMixin, TimestampMixin):
    """SLA metric snapshot for moderation pipeline performance."""

    __tablename__ = "sla_metrics"

    pipeline: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
    )  # pre_publish, post_publish
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    p95_ms: Mapped[float] = mapped_column(
        nullable=False, default=0.0,
    )
    items_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    items_in_sla: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    items_breached_sla: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )


class PatternDetection(Base, UUIDMixin, TimestampMixin):
    """Detected content pattern from moderation analysis."""

    __tablename__ = "pattern_detections"

    pattern_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
    )  # keyword_spike, user_repeat_offender, content_type_surge, risk_category_trend
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="low",
    )  # low, medium, high, critical
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    acknowledged: Mapped[bool] = mapped_column(
        nullable=False, default=False,
    )
