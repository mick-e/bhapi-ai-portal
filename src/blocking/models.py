"""Blocking models — rules for blocking AI session access."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class BlockRule(Base, UUIDMixin, TimestampMixin):
    """Rule to block a member from accessing AI platforms."""
    __tablename__ = "block_rules"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    platforms: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )  # null = all platforms
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auto_block_rules.id"), nullable=True
    )


class AutoBlockRule(Base, UUIDMixin, TimestampMixin):
    """Configurable trigger that auto-creates BlockRules."""

    __tablename__ = "auto_block_rules"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # risk_event_count, spend_threshold, time_of_day
    trigger_config: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_window_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_start: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # HH:MM for time_of_day
    schedule_end: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, default="block_all"
    )  # block_all, block_platform
    platforms: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=True
    )  # null = all members
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
