"""Screen time management database models — rules, schedules, extension requests."""

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class ScreenTimeRule(Base, UUIDMixin, TimestampMixin):
    """Per-app or per-category screen time limit for a child."""

    __tablename__ = "screen_time_rules"
    __table_args__ = (
        Index("ix_screen_time_rules_group_member", "group_id", "member_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    app_category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="all",
    )  # social, games, education, entertainment, productivity, all
    daily_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    age_tier_enforcement: Mapped[str] = mapped_column(
        String(30), nullable=False, default="warning_then_block",
    )  # hard_block, warning_then_block, warning_only
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ScreenTimeSchedule(Base, UUIDMixin, TimestampMixin):
    """Time-of-day schedule attached to a screen time rule."""

    __tablename__ = "screen_time_schedules"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("screen_time_rules.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    day_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="weekday",
    )  # weekday, weekend, custom
    blocked_start: Mapped[time] = mapped_column(Time, nullable=False)
    blocked_end: Mapped[time] = mapped_column(Time, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ExtensionRequest(Base, UUIDMixin, TimestampMixin):
    """Child's request for more screen time."""

    __tablename__ = "extension_requests"
    __table_args__ = (
        Index("ix_extension_requests_member_status", "member_id", "status"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("screen_time_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, denied, expired
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
