"""Device agent database models — sessions, app usage, screen time."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class DeviceSession(Base, UUIDMixin, TimestampMixin):
    """A device session representing when the safety agent was active."""

    __tablename__ = "device_sessions"
    __table_args__ = (
        Index("ix_device_sessions_member_started", "member_id", "started_at"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # ios, android, tablet
    os_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)


class AppUsageRecord(Base, UUIDMixin, TimestampMixin):
    """Individual app usage event from the device agent."""

    __tablename__ = "app_usage_records"
    __table_args__ = (
        Index("ix_app_usage_member_started", "member_id", "started_at"),
        Index("ix_app_usage_member_category", "member_id", "category"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bundle_id: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other",
    )  # social, education, games, entertainment, productivity, other
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    foreground_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class ScreenTimeRecord(Base, UUIDMixin, TimestampMixin):
    """Daily screen time summary for a member."""

    __tablename__ = "screen_time_records"
    __table_args__ = (
        Index("ix_screen_time_member_date", "member_id", "date", unique=True),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    app_breakdown: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    category_breakdown: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    pickups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
