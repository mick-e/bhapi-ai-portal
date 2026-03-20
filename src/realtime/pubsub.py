"""Redis pub/sub event bridge between monolith and real-time service."""

import asyncio
import json

import structlog

logger = structlog.get_logger()


class EventBridge:
    """Subscribes to Redis channels and dispatches events to WebSocket connections."""

    def __init__(self, connection_manager):
        self._manager = connection_manager
        self._redis = None
        self._pubsub = None
        self._running = False

    async def start(self, redis_url: str | None = None):
        """Start listening to Redis pub/sub channels."""
        if not redis_url:
            logger.info("pubsub_disabled", reason="no redis URL")
            return

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(redis_url)
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("alerts", "social", "moderation")
            self._running = True
            logger.info(
                "pubsub_started", channels=["alerts", "social", "moderation"]
            )
        except Exception as e:
            logger.warning("pubsub_start_failed", error=str(e))

    async def stop(self):
        """Stop listening."""
        self._running = False
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def listen(self):
        """Listen for messages and dispatch to connections."""
        if not self._pubsub:
            return

        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    await self._handle_message(message)
            except Exception as e:
                logger.error("pubsub_error", error=str(e))
                await asyncio.sleep(1)

    async def _handle_message(self, message: dict):
        """Route a pub/sub message to the appropriate connections."""
        try:
            data = json.loads(message["data"])
            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()

            target_user_id = data.get("target_user_id")
            target_room = data.get("target_room")

            if target_user_id:
                await self._manager.send_to_user(target_user_id, data)
            elif target_room:
                await self._manager.broadcast_room(target_room, data)
            else:
                logger.warning("pubsub_no_target", channel=channel)
        except json.JSONDecodeError as e:
            logger.error("pubsub_invalid_json", error=str(e))
        except Exception as e:
            logger.error("pubsub_handle_error", error=str(e))

    async def publish(self, channel: str, data: dict):
        """Publish a message to a Redis channel (for testing/monolith use)."""
        if self._redis:
            await self._redis.publish(channel, json.dumps(data))
