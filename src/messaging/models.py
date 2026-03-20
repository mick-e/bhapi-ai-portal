"""Messaging database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Chat conversation (direct or group)."""

    __tablename__ = "conversations"

    type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # direct, group
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ConversationMember(Base, UUIDMixin, TimestampMixin):
    """Member of a conversation."""

    __tablename__ = "conversation_members"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member",
    )  # member, admin


class Message(Base, UUIDMixin, TimestampMixin):
    """Message in a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text",
    )  # text, image, video, system
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )


class MessageMedia(Base, UUIDMixin, TimestampMixin):
    """Media attachment on a message."""

    __tablename__ = "message_media"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cloudflare_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # image, video
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )
