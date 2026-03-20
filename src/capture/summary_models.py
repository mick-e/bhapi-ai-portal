"""Conversation summary database models."""

import uuid
from datetime import date as date_type

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class ConversationSummary(Base, UUIDMixin, TimestampMixin):
    """LLM-generated summary of a child's AI conversation for parents."""

    __tablename__ = "conversation_summaries"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    capture_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture_events.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    topics: Mapped[list] = mapped_column(JSONType, default=list)
    emotional_tone: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="neutral"
    )  # neutral, positive, concerned, distressed
    risk_flags: Mapped[list] = mapped_column(JSONType, default=list)
    key_quotes: Mapped[list] = mapped_column(JSONType, default=list)  # max 3
    action_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    detail_level: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="full"
    )  # full, moderate, minimal
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA-256 dedup

    __table_args__ = (
        Index(
            "ix_conv_summaries_group_member_date",
            "group_id",
            "member_id",
            "date",
        ),
        Index(
            "ix_conv_summaries_group_action",
            "group_id",
            "action_needed",
            "date",
        ),
    )
