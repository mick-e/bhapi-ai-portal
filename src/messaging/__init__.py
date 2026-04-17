"""Messaging — conversations, real-time chat, media messages.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.messaging.schemas import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ConversationWithUnread,
    MediaMessageCreate,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    ReadReceiptCreate,
    TypingIndicator,
    TypingStatusResponse,
    UnreadCountResponse,
)
# Public interface for cross-module access
from .models import ConversationMember, Message

from src.messaging.service import (
    create_conversation,
    get_conversation,
    get_unread_count,
    list_conversations,
    list_messages,
    mark_read,
    send_media_message,
    send_message,
)

__all__ = [
    "ConversationCreate",
    "ConversationListResponse",
    "ConversationResponse",
    "ConversationWithUnread",
    "MediaMessageCreate",
    "MessageCreate",
    "MessageListResponse",
    "MessageResponse",
    "ReadReceiptCreate",
    "TypingIndicator",
    "TypingStatusResponse",
    "UnreadCountResponse",
    "create_conversation",
    "get_conversation",
    "get_unread_count",
    "list_conversations",
    "list_messages",
    "mark_read",
    "send_media_message",
    "send_message",
    "ConversationMember",
    "Message",
]
