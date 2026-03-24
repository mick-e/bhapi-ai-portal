"""Alerts database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class Alert(Base, UUIDMixin, TimestampMixin):
    """A notification alert sent to a group or member."""

    __tablename__ = "alerts"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=True
    )
    risk_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ai", server_default="ai"
    )  # ai, social, device
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # critical, high, medium, low, info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="portal"
    )  # portal, email
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, sent, acknowledged
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    re_notify_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    snoozed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    renotify_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    enriched_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enriched_alerts.id", use_alter=True, name="fk_alerts_enriched_alert_id"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_alerts_group_severity_created", "group_id", "severity", "created_at"),
        Index("ix_alerts_group_status_created", "group_id", "status", "created_at"),
        Index("ix_alerts_group_source_created", "group_id", "source", "created_at"),
    )


class NotificationPreference(Base, UUIDMixin, TimestampMixin):
    """User notification preferences per group and category."""

    __tablename__ = "notification_preferences"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # risk_alert, spend_alert, report, system
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="portal"
    )  # portal, email
    digest_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="immediate"
    )  # immediate, hourly, daily
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
