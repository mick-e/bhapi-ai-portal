"""Messaging module Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    type: str = Field(default="direct", description="Conversation type: direct or group")
    title: str | None = Field(default=None, max_length=255)
    member_user_ids: list[UUID] = Field(
        ..., description="User IDs to add as members (creator is added automatically)",
    )


class ConversationResponse(BaseModel):
    """Schema for a conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str | None
    created_by: UUID
    member_count: int
    created_at: datetime


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


class MessageCreate(BaseModel):
    """Schema for sending a message."""

    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text")


class MessageResponse(BaseModel):
    """Schema for a message response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    message_type: str
    moderation_status: str
    created_at: datetime


class MessageListResponse(BaseModel):
    """Paginated list of messages."""

    items: list[MessageResponse]
    total: int
    page: int
    page_size: int


class MediaMessageCreate(BaseModel):
    """Schema for sending a media message."""

    content: str = Field(default="", description="Optional caption text")
    message_type: str = Field(default="image", description="image or video")
    media_url: str = Field(..., min_length=1, description="Cloudflare media URL or ID")
    media_type: str = Field(default="image", description="image or video")


class TypingIndicator(BaseModel):
    """Schema for typing indicator requests."""

    conversation_id: UUID


class TypingStatusResponse(BaseModel):
    """Schema for typing status response."""

    conversation_id: UUID
    typing_users: list[str]


class UnreadCountResponse(BaseModel):
    """Schema for unread count response."""

    conversation_id: UUID
    unread_count: int


class ReadReceiptCreate(BaseModel):
    """Schema for creating a read receipt."""

    conversation_id: UUID


class ConversationWithUnread(ConversationResponse):
    """Conversation response with unread count and last message preview."""

    unread_count: int = 0
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
