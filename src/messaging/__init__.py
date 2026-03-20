"""Messaging — conversations, real-time chat, media messages.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.messaging.schemas import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)
from src.messaging.service import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    mark_read,
    send_message,
)

__all__ = [
    "ConversationCreate",
    "ConversationListResponse",
    "ConversationResponse",
    "MessageCreate",
    "MessageListResponse",
    "MessageResponse",
    "create_conversation",
    "get_conversation",
    "list_conversations",
    "list_messages",
    "mark_read",
    "send_message",
]
