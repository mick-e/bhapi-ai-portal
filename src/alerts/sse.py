"""Server-Sent Events manager for real-time alert streaming."""

import asyncio
import json
from uuid import UUID

import structlog

logger = structlog.get_logger()


class SSEConnectionManager:
    """Manages SSE connections per group for real-time alert push."""

    def __init__(self):
        self._connections: dict[UUID, list[asyncio.Queue]] = {}

    def connect(self, group_id: UUID) -> asyncio.Queue:
        """Register a new SSE listener for a group."""
        queue: asyncio.Queue = asyncio.Queue()
        if group_id not in self._connections:
            self._connections[group_id] = []
        self._connections[group_id].append(queue)
        logger.info("sse_connected", group_id=str(group_id), total=len(self._connections[group_id]))
        return queue

    def disconnect(self, group_id: UUID, queue: asyncio.Queue) -> None:
        """Remove an SSE listener."""
        if group_id in self._connections:
            try:
                self._connections[group_id].remove(queue)
            except ValueError:
                pass
            if not self._connections[group_id]:
                del self._connections[group_id]
            logger.info("sse_disconnected", group_id=str(group_id))

    async def broadcast(self, group_id: UUID, event_type: str, data: dict) -> int:
        """Send an event to all listeners for a group. Returns count of listeners notified."""
        if group_id not in self._connections:
            return 0
        message = f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
        count = 0
        for queue in self._connections[group_id]:
            try:
                await queue.put(message)
                count += 1
            except Exception:
                pass
        return count

    @property
    def connection_count(self) -> int:
        return sum(len(qs) for qs in self._connections.values())


# Global singleton
sse_manager = SSEConnectionManager()
