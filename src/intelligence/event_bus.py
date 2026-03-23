"""Intelligence event bus — Redis pub/sub for cross-module event correlation.

Channels:
- bhapi:events:ai_session — AI platform usage events from capture module
- bhapi:events:social_activity — Social feed/messaging events from social module
- bhapi:events:device — Device agent events (app usage, screen time)
- bhapi:events:location — Location events (geofence, check-in)

Events are JSON payloads with structure:
  {"timestamp": "ISO8601", "event_type": "channel_name", "data": {...}}
"""

import json
from datetime import datetime, timezone

import structlog

from src.redis_client import get_redis

logger = structlog.get_logger()

# Channel constants
EVENT_AI_SESSION = "bhapi:events:ai_session"
EVENT_SOCIAL_ACTIVITY = "bhapi:events:social_activity"
EVENT_DEVICE = "bhapi:events:device"
EVENT_LOCATION = "bhapi:events:location"

ALL_CHANNELS = [EVENT_AI_SESSION, EVENT_SOCIAL_ACTIVITY, EVENT_DEVICE, EVENT_LOCATION]


async def publish_event(channel: str, data: dict) -> None:
    """Publish an event to a Redis channel.

    Gracefully degrades if Redis is unavailable (logs warning, does not raise).
    """
    redis = get_redis()
    if redis is None:
        logger.warning("event_bus_no_redis", channel=channel)
        return

    payload = json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": channel,
        "data": data,
    })
    try:
        await redis.publish(channel, payload)
        logger.debug("event_published", channel=channel)
    except Exception as exc:
        logger.warning("event_publish_failed", channel=channel, error=str(exc))


def subscribe(channels: list[str] | None = None):
    """Subscribe to event channels. Returns an async generator of events, or None if Redis unavailable.

    Usage:
        gen = subscribe([EVENT_AI_SESSION])
        if gen is not None:
            async for event in gen:
                process(event)
    """
    redis = get_redis()
    if redis is None:
        logger.warning("event_bus_subscribe_no_redis")
        return None

    sub_channels = channels or ALL_CHANNELS
    return _subscribe_generator(redis, sub_channels)


async def _subscribe_generator(redis, sub_channels: list[str]):
    """Internal async generator for Redis pub/sub subscription."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(*sub_channels)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("event_bus_invalid_json", data=message["data"])
    finally:
        await pubsub.unsubscribe(*sub_channels)
        await pubsub.close()


class EventBus:
    """Convenience class wrapping module-level publish_event and subscribe functions.

    Useful for dependency injection and testing scenarios where a class instance
    is preferred over bare module functions.
    """

    async def publish(self, channel: str, data: dict) -> None:
        """Publish an event to a Redis channel."""
        await publish_event(channel, data)

    def subscribe(self, channels: list[str] | None = None):
        """Subscribe to event channels. Returns async generator or None."""
        return subscribe(channels)
