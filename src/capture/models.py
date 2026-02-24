"""Capture gateway database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class CaptureEvent(Base, UUIDMixin, TimestampMixin):
    """Captured AI interaction event."""

    __tablename__ = "capture_events"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # chatgpt, gemini, copilot, claude, grok
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # prompt, response, session_start, session_end
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column("event_metadata", JSONType, nullable=True)
    risk_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="extension")  # extension, dns, api

    __table_args__ = (
        Index("ix_capture_events_group_member_ts", "group_id", "member_id", "timestamp"),
        Index("ix_capture_events_group_platform_ts", "group_id", "platform", "timestamp"),
    )


class DeviceRegistration(Base, UUIDMixin, TimestampMixin):
    """Registered device with browser extension."""

    __tablename__ = "device_registrations"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    setup_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    extension_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
