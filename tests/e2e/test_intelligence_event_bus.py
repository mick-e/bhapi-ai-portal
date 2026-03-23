"""E2E tests for intelligence event bus.

These tests run against the in-memory test environment (no real Redis required).
Redis is not available in the test environment — tests verify graceful degradation
and payload correctness via mocking.
"""

import json

import pytest
from unittest.mock import AsyncMock, patch

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
# Publish from each channel — 4 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_ai_session_event():
    """Publish an ai_session event and verify channel + payload structure."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(
            EVENT_AI_SESSION,
            {"child_id": "c1", "platform": "chatgpt", "duration_s": 120},
        )
        mock_redis.publish.assert_called_once()
        channel, raw = mock_redis.publish.call_args[0]
        assert channel == "bhapi:events:ai_session"
        payload = json.loads(raw)
        assert payload["event_type"] == EVENT_AI_SESSION
        assert payload["data"]["platform"] == "chatgpt"
        assert "timestamp" in payload


@pytest.mark.asyncio
async def test_publish_social_activity_event():
    """Publish a social_activity event and verify channel + payload structure."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(
            EVENT_SOCIAL_ACTIVITY,
            {"user_id": "u1", "action": "post", "content_length": 80},
        )
        mock_redis.publish.assert_called_once()
        channel, raw = mock_redis.publish.call_args[0]
        assert channel == "bhapi:events:social_activity"
        payload = json.loads(raw)
        assert payload["event_type"] == EVENT_SOCIAL_ACTIVITY
        assert payload["data"]["action"] == "post"


@pytest.mark.asyncio
async def test_publish_device_event():
    """Publish a device event and verify channel + payload structure."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(
            EVENT_DEVICE,
            {"device_id": "d1", "app": "youtube", "screen_time_s": 300},
        )
        mock_redis.publish.assert_called_once()
        channel, raw = mock_redis.publish.call_args[0]
        assert channel == "bhapi:events:device"
        payload = json.loads(raw)
        assert payload["event_type"] == EVENT_DEVICE
        assert payload["data"]["app"] == "youtube"


@pytest.mark.asyncio
async def test_publish_location_event():
    """Publish a location event and verify channel + payload structure."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(
            EVENT_LOCATION,
            {"child_id": "c2", "lat": 40.7128, "lon": -74.0060, "geofence": "school"},
        )
        mock_redis.publish.assert_called_once()
        channel, raw = mock_redis.publish.call_args[0]
        assert channel == "bhapi:events:location"
        payload = json.loads(raw)
        assert payload["event_type"] == EVENT_LOCATION
        assert payload["data"]["geofence"] == "school"


# ---------------------------------------------------------------------------
# Graceful degradation without Redis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_ai_session_graceful_without_redis():
    """publish_event for AI session doesn't raise when Redis unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        await publish_event(EVENT_AI_SESSION, {"child_id": "c1"})


@pytest.mark.asyncio
async def test_publish_all_channels_graceful_without_redis():
    """All four channels degrade gracefully when Redis is unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        for channel in ALL_CHANNELS:
            await publish_event(channel, {"test": True})


@pytest.mark.asyncio
async def test_subscribe_returns_none_without_redis():
    """subscribe() returns None (not an async generator) when Redis unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        result = subscribe()
        assert result is None


# ---------------------------------------------------------------------------
# Payload structure validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_payload_structure_has_three_top_level_keys():
    """Every published event payload has exactly timestamp, event_type, and data."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, {"x": 1})
        raw = mock_redis.publish.call_args[0][1]
        payload = json.loads(raw)
        assert set(payload.keys()) == {"timestamp", "event_type", "data"}


@pytest.mark.asyncio
async def test_event_type_matches_channel():
    """The event_type field in the payload matches the channel argument."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        for channel in ALL_CHANNELS:
            mock_redis.reset_mock()
            await publish_event(channel, {})
            raw = mock_redis.publish.call_args[0][1]
            payload = json.loads(raw)
            assert payload["event_type"] == channel


@pytest.mark.asyncio
async def test_data_round_trips_correctly():
    """The data dict is preserved exactly in the published payload."""
    mock_redis = AsyncMock()
    original = {"child_id": "c1", "score": 87, "flags": ["late_night", "sensitive_topic"]}
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, original)
        raw = mock_redis.publish.call_args[0][1]
        payload = json.loads(raw)
        assert payload["data"] == original


# ---------------------------------------------------------------------------
# Sequential publishing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_publish_all_channels():
    """Publishing to all four channels in sequence results in four redis.publish calls."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        for channel in ALL_CHANNELS:
            await publish_event(channel, {"seq": channel})
        assert mock_redis.publish.call_count == 4
        called_channels = [c[0][0] for c in mock_redis.publish.call_args_list]
        assert called_channels == ALL_CHANNELS


# ---------------------------------------------------------------------------
# EventBus class E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_bus_class_publish_ai_session():
    """EventBus.publish() correctly routes AI session events."""
    mock_redis = AsyncMock()
    bus = EventBus()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await bus.publish(EVENT_AI_SESSION, {"child_id": "c1", "platform": "claude"})
        mock_redis.publish.assert_called_once()
        channel = mock_redis.publish.call_args[0][0]
        assert channel == EVENT_AI_SESSION


@pytest.mark.asyncio
async def test_event_bus_class_subscribe_without_redis():
    """EventBus.subscribe() returns None when Redis is unavailable."""
    bus = EventBus()
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        result = bus.subscribe()
        assert result is None


@pytest.mark.asyncio
async def test_imports_from_intelligence_package():
    """All event bus symbols are importable from src.intelligence package."""
    from src.intelligence import (
        EVENT_AI_SESSION,
        EVENT_DEVICE,
        EVENT_LOCATION,
        EVENT_SOCIAL_ACTIVITY,
        publish_event,
        subscribe,
    )
    assert EVENT_AI_SESSION == "bhapi:events:ai_session"
    assert EVENT_SOCIAL_ACTIVITY == "bhapi:events:social_activity"
    assert EVENT_DEVICE == "bhapi:events:device"
    assert EVENT_LOCATION == "bhapi:events:location"
    assert callable(publish_event)
    assert callable(subscribe)
