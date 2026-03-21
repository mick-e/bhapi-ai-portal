"""Typing indicator manager — in-memory, timeout-based expiry."""

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()

# Typing indicator expires after this many seconds
TYPING_TIMEOUT_SECONDS = 5.0


@dataclass
class TypingState:
    user_id: str
    conversation_id: str
    started_at: datetime


class TypingManager:
    """In-memory typing indicator tracking with auto-expiry.

    Each user can be typing in at most one conversation at a time.
    Typing state auto-expires after TYPING_TIMEOUT_SECONDS.
    """

    def __init__(self, timeout_seconds: float = TYPING_TIMEOUT_SECONDS):
        self._typing: dict[str, TypingState] = {}  # user_id -> TypingState
        self._timeout = timeout_seconds

    def start_typing(self, user_id: str, conversation_id: str) -> None:
        """Mark a user as typing in a conversation."""
        self._typing[user_id] = TypingState(
            user_id=user_id,
            conversation_id=conversation_id,
            started_at=datetime.now(timezone.utc),
        )
        logger.debug(
            "typing_started",
            user_id=user_id,
            conversation_id=conversation_id,
        )

    def stop_typing(self, user_id: str) -> None:
        """Mark a user as no longer typing."""
        removed = self._typing.pop(user_id, None)
        if removed:
            logger.debug("typing_stopped", user_id=user_id)

    def is_typing(self, user_id: str, conversation_id: str | None = None) -> bool:
        """Check if a user is currently typing (not expired).

        If conversation_id is provided, also checks that the user is typing
        in that specific conversation.
        """
        state = self._typing.get(user_id)
        if not state:
            return False

        # Check expiry
        elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        if elapsed >= self._timeout:
            self._typing.pop(user_id, None)
            return False

        if conversation_id and state.conversation_id != conversation_id:
            return False

        return True

    def get_typing_users(self, conversation_id: str) -> list[str]:
        """Get list of user IDs currently typing in a conversation."""
        now = datetime.now(timezone.utc)
        typing_users = []
        expired = []

        for user_id, state in self._typing.items():
            if state.conversation_id != conversation_id:
                continue
            elapsed = (now - state.started_at).total_seconds()
            if elapsed >= self._timeout:
                expired.append(user_id)
            else:
                typing_users.append(user_id)

        # Clean up expired entries
        for user_id in expired:
            self._typing.pop(user_id, None)

        return typing_users

    def clear(self) -> None:
        """Clear all typing state."""
        self._typing.clear()

    @property
    def active_count(self) -> int:
        """Number of users currently marked as typing (may include expired)."""
        return len(self._typing)


# Module-level singleton
typing_manager = TypingManager()
