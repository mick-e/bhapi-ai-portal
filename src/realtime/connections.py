"""WebSocket connection manager."""

import asyncio
import json
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections per user with room-based messaging."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}  # user_id -> websocket
        self._rooms: dict[str, set[str]] = {}  # room_name -> set of user_ids
        self._last_heartbeat: dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register a new connection."""
        await websocket.accept()
        # Close existing connection for this user if any
        if user_id in self._connections:
            try:
                await self._connections[user_id].close(
                    code=4000, reason="New connection"
                )
            except Exception:
                pass
        self._connections[user_id] = websocket
        self._last_heartbeat[user_id] = datetime.now(timezone.utc)
        logger.info("ws_connected", user_id=user_id, total=len(self._connections))

    async def disconnect(self, user_id: str):
        """Remove a connection."""
        self._connections.pop(user_id, None)
        self._last_heartbeat.pop(user_id, None)
        # Remove from all rooms
        for room_users in self._rooms.values():
            room_users.discard(user_id)
        logger.info("ws_disconnected", user_id=user_id, total=len(self._connections))

    def join_room(self, user_id: str, room: str):
        """Add user to a room."""
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(user_id)

    def leave_room(self, user_id: str, room: str):
        """Remove user from a room."""
        if room in self._rooms:
            self._rooms[room].discard(user_id)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to a specific user."""
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(user_id)

    async def broadcast_room(
        self, room: str, message: dict, exclude: str | None = None
    ):
        """Send message to all users in a room."""
        users = self._rooms.get(room, set())
        for user_id in list(users):
            if user_id != exclude:
                await self.send_to_user(user_id, message)

    async def broadcast_all(self, message: dict):
        """Send message to all connected users."""
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)

    def heartbeat(self, user_id: str):
        """Update heartbeat timestamp."""
        self._last_heartbeat[user_id] = datetime.now(timezone.utc)

    def is_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected."""
        return user_id in self._connections

    def get_connected_count(self) -> int:
        """Return the number of active connections."""
        return len(self._connections)

    def get_room_members(self, room: str) -> set[str]:
        """Return a copy of the set of user IDs in a room."""
        return self._rooms.get(room, set()).copy()
