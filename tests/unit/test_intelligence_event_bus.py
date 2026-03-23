"""Unit tests for intelligence event bus."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.intelligence.event_bus import (
    ALL_CHANNELS,
    EventBus,
    publish_event,
    subscribe,
    EVENT_AI_SESSION,
    EVENT_SOCIAL_ACTIVITY,
    EVENT_DEVICE,
    EVENT_LOCATION,
)


# ---------------------------------------------------------------------------
# Channel constant tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_channels_are_defined():
    """All four event channel constants are defined."""
    assert EVENT_AI_SESSION == "bhapi:events:ai_session"
    assert EVENT_SOCIAL_ACTIVITY == "bhapi:events:social_activity"
    assert EVENT_DEVICE == "bhapi:events:device"
    assert EVENT_LOCATION == "bhapi:events:location"


def test_all_channels_list_contains_all_constants():
    """ALL_CHANNELS includes all four channel constants."""
    assert EVENT_AI_SESSION in ALL_CHANNELS
    assert EVENT_SOCIAL_ACTIVITY in ALL_CHANNELS
    assert EVENT_DEVICE in ALL_CHANNELS
    assert EVENT_LOCATION in ALL_CHANNELS
    assert len(ALL_CHANNELS) == 4


def test_channel_names_have_correct_prefix():
    """All channels share the bhapi:events: prefix."""
    for channel in ALL_CHANNELS:
        assert channel.startswith("bhapi:events:"), f"{channel!r} missing prefix"


# ---------------------------------------------------------------------------
# publish_event — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_event_formats_channel():
    """publish_event sends JSON payload to correct Redis channel."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, {"child_id": "abc", "platform": "chatgpt"})
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "bhapi:events:ai_session"


@pytest.mark.asyncio
async def test_publish_event_includes_timestamp():
    """Published events include a timestamp field."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_DEVICE, {"device_id": "d1"})
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert "timestamp" in payload
        assert "data" in payload


@pytest.mark.asyncio
async def test_publish_event_includes_event_type():
    """Published payload has event_type matching the channel."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_SOCIAL_ACTIVITY, {"user_id": "u1"})
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["event_type"] == EVENT_SOCIAL_ACTIVITY


@pytest.mark.asyncio
async def test_publish_event_data_round_trips():
    """The data dict is preserved verbatim inside the payload."""
    mock_redis = AsyncMock()
    original_data = {"child_id": "c1", "platform": "gemini", "score": 42}
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, original_data)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data"] == original_data


@pytest.mark.asyncio
async def test_publish_event_payload_is_valid_json():
    """The second argument to redis.publish is valid JSON string."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_LOCATION, {"lat": 51.5, "lon": -0.1})
        raw = mock_redis.publish.call_args[0][1]
        # Should not raise
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_publish_event_empty_data_dict():
    """publish_event works with an empty data dict."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_DEVICE, {})
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data"] == {}


@pytest.mark.asyncio
async def test_publish_event_nested_data():
    """Nested data structures serialise correctly."""
    mock_redis = AsyncMock()
    nested = {"child": {"id": "c1", "age": 10}, "platforms": ["chatgpt", "gemini"]}
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, nested)
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert payload["data"] == nested


@pytest.mark.asyncio
async def test_publish_event_large_payload():
    """Large payloads (e.g. 1000 key dict) are published without error."""
    mock_redis = AsyncMock()
    large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, large_data)
        mock_redis.publish.assert_called_once()
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert len(payload["data"]) == 1000


# ---------------------------------------------------------------------------
# publish_event — multiple sequential calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_multiple_events_sequentially():
    """Multiple publish_event calls each invoke redis.publish once."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, {"n": 1})
        await publish_event(EVENT_SOCIAL_ACTIVITY, {"n": 2})
        await publish_event(EVENT_DEVICE, {"n": 3})
        assert mock_redis.publish.call_count == 3


@pytest.mark.asyncio
async def test_publish_multiple_events_correct_channels():
    """Sequential publishes go to their respective channels."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, {})
        await publish_event(EVENT_LOCATION, {})
        calls = mock_redis.publish.call_args_list
        assert calls[0][0][0] == EVENT_AI_SESSION
        assert calls[1][0][0] == EVENT_LOCATION


# ---------------------------------------------------------------------------
# publish_event — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_event_graceful_without_redis():
    """publish_event degrades gracefully when Redis is unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        # Should not raise
        await publish_event(EVENT_AI_SESSION, {"child_id": "abc"})


@pytest.mark.asyncio
async def test_publish_event_graceful_on_redis_exception():
    """publish_event catches Redis errors and does not propagate them."""
    mock_redis = AsyncMock()
    mock_redis.publish.side_effect = ConnectionError("Redis down")
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        # Should not raise
        await publish_event(EVENT_AI_SESSION, {"child_id": "abc"})


# ---------------------------------------------------------------------------
# subscribe — without Redis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_returns_none_without_redis():
    """subscribe returns None (not an async generator) when Redis unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        result = subscribe()
        assert result is None


@pytest.mark.asyncio
async def test_subscribe_accepts_channel_list():
    """subscribe can be called with a subset of channels without error."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        result = subscribe([EVENT_AI_SESSION, EVENT_DEVICE])
        assert result is None


# ---------------------------------------------------------------------------
# EventBus class (if exposed)
# ---------------------------------------------------------------------------


def test_event_bus_class_exists():
    """EventBus class is importable from event_bus module."""
    assert EventBus is not None


@pytest.mark.asyncio
async def test_event_bus_publish_delegates_to_publish_event():
    """EventBus.publish() delegates to the module-level publish_event."""
    mock_redis = AsyncMock()
    bus = EventBus()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await bus.publish(EVENT_AI_SESSION, {"test": True})
        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == EVENT_AI_SESSION
