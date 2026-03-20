"""Presence system — online/offline/last-seen tracking."""

from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


@dataclass
class PresenceInfo:
    user_id: str
    is_online: bool
    last_seen: datetime | None


class PresenceTracker:
    """In-memory presence tracking (Redis upgrade in production)."""

    def __init__(self):
        self._online: set[str] = set()
        self._last_seen: dict[str, datetime] = {}

    def set_online(self, user_id: str):
        self._online.add(user_id)
        self._last_seen[user_id] = datetime.now(timezone.utc)

    def set_offline(self, user_id: str):
        self._online.discard(user_id)
        self._last_seen[user_id] = datetime.now(timezone.utc)

    def get_presence(self, user_id: str) -> PresenceInfo:
        return PresenceInfo(
            user_id=user_id,
            is_online=user_id in self._online,
            last_seen=self._last_seen.get(user_id),
        )

    def get_online_users(self, user_ids: list[str] | None = None) -> list[str]:
        """Get online users, optionally filtered to a subset."""
        if user_ids is not None:
            return [uid for uid in user_ids if uid in self._online]
        return list(self._online)

    def get_online_count(self) -> int:
        return len(self._online)


tracker = PresenceTracker()
