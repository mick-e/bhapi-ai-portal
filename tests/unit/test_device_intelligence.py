"""Unit tests for device agent → intelligence event bus wiring."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.device_agent.schemas import AppUsageCreate, DeviceSessionCreate, DeviceSyncRequest
from src.device_agent.service import AI_APP_BUNDLES, record_app_usage, sync_device_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db():
    """Return a minimal mock that satisfies service.py's DB calls.

    db.add() is synchronous (SQLAlchemy's Session.add is not a coroutine).
    db.flush() and db.refresh() are async (SQLAlchemy async session methods).
    db.execute() is async and returns a synchronous-chainable result object.
    """
    db = AsyncMock()
    # add() is synchronous in SQLAlchemy — must NOT be an AsyncMock
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    # Build a synchronous result object: execute() is async but returns a
    # plain object whose .scalar(), .scalar_one_or_none(), .scalars() are sync.
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []

    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value = mock_scalars

    db.execute = AsyncMock(return_value=mock_result)
    return db


def _make_app_usage_data(bundle_id: str, member_id=None) -> AppUsageCreate:
    return AppUsageCreate(
        member_id=member_id or uuid.uuid4(),
        app_name="Test App",
        bundle_id=bundle_id,
        category="productivity",
        started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
        foreground_minutes=15.0,
    )


def _make_sync_request(member_id=None, sessions=None, usage_records=None) -> DeviceSyncRequest:
    return DeviceSyncRequest(
        member_id=member_id or uuid.uuid4(),
        device_id="test-device-001",
        device_type="ios",
        sessions=sessions or [],
        usage_records=usage_records or [],
    )


# ---------------------------------------------------------------------------
# Test 1: sync_device_data publishes device event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_device_data_publishes_device_event():
    """sync_device_data publishes a 'device_sync' event to the 'device' channel."""
    db = _make_mock_db()
    group_id = uuid.uuid4()
    member_id = uuid.uuid4()

    sync_req = _make_sync_request(member_id=member_id)

    with patch("src.device_agent.service._publish_intelligence_event", new_callable=AsyncMock) as mock_publish:
        await sync_device_data(db, group_id, sync_req)

    mock_publish.assert_awaited_once()
    call_args = mock_publish.call_args
    channel, event_data = call_args[0]

    assert channel == "device"
    assert event_data["type"] == "device_sync"
    assert event_data["member_id"] == str(member_id)
    assert event_data["group_id"] == str(group_id)
    assert "sessions_count" in event_data
    assert "usage_count" in event_data


# ---------------------------------------------------------------------------
# Test 2: record_app_usage with AI bundle publishes ai_session event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_app_usage_ai_bundle_publishes_event():
    """record_app_usage with an AI bundle ID publishes an 'ai_app_usage' event."""
    db = _make_mock_db()
    group_id = uuid.uuid4()
    member_id = uuid.uuid4()

    # Use a known AI bundle
    data = _make_app_usage_data(bundle_id="com.openai.chatgpt", member_id=member_id)

    with patch("src.device_agent.service._publish_intelligence_event", new_callable=AsyncMock) as mock_publish:
        await record_app_usage(db, group_id, data)

    mock_publish.assert_awaited_once()
    call_args = mock_publish.call_args
    channel, event_data = call_args[0]

    assert channel == "ai_session"
    assert event_data["type"] == "ai_app_usage"
    assert event_data["member_id"] == str(member_id)
    assert event_data["bundle_id"] == "com.openai.chatgpt"
    assert event_data["foreground_minutes"] == 15.0


# ---------------------------------------------------------------------------
# Test 3: record_app_usage with non-AI bundle does NOT publish ai_session event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_app_usage_non_ai_bundle_no_event():
    """record_app_usage with a non-AI bundle ID does NOT publish any event."""
    db = _make_mock_db()
    group_id = uuid.uuid4()

    data = _make_app_usage_data(bundle_id="com.apple.safari")
    assert data.bundle_id not in AI_APP_BUNDLES

    with patch("src.device_agent.service._publish_intelligence_event", new_callable=AsyncMock) as mock_publish:
        await record_app_usage(db, group_id, data)

    mock_publish.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 4: publish failure does NOT block sync_device_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_device_data_publish_failure_does_not_raise():
    """If the intelligence event bus raises, sync_device_data still returns normally.

    _publish_intelligence_event catches all exceptions internally (best-effort).
    We simulate the inner publish_event failing and verify the sync result is
    still returned rather than an exception propagating to the caller.
    """
    db = _make_mock_db()
    group_id = uuid.uuid4()

    sync_req = _make_sync_request()

    # Patch the inner publish_event that _publish_intelligence_event imports
    # at call time.  The helper's try/except will catch the RuntimeError and
    # log a warning — sync_device_data must not re-raise.
    with patch("src.intelligence.publish_event", new_callable=AsyncMock, side_effect=RuntimeError("redis down")):
        result = await sync_device_data(db, group_id, sync_req)

    assert "sessions_created" in result
    assert "usage_records_created" in result
    assert "screen_time_updated" in result


# ---------------------------------------------------------------------------
# Test 5: publish failure does NOT block record_app_usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_app_usage_publish_failure_does_not_raise():
    """If the intelligence event bus raises, record_app_usage still returns normally."""
    db = _make_mock_db()
    group_id = uuid.uuid4()

    data = _make_app_usage_data(bundle_id="com.anthropic.claude")
    assert data.bundle_id in AI_APP_BUNDLES

    with patch("src.intelligence.publish_event", new_callable=AsyncMock, side_effect=Exception("bus unavailable")):
        record = await record_app_usage(db, group_id, data)

    # record_app_usage still returned the refreshed ORM object
    assert record is not None


# ---------------------------------------------------------------------------
# Test 6: All AI_APP_BUNDLES are recognised
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_ai_bundles_trigger_event():
    """Every bundle in AI_APP_BUNDLES triggers an ai_session publish."""
    group_id = uuid.uuid4()

    for bundle_id in AI_APP_BUNDLES:
        db = _make_mock_db()
        data = _make_app_usage_data(bundle_id=bundle_id)

        with patch("src.device_agent.service._publish_intelligence_event", new_callable=AsyncMock) as mock_publish:
            await record_app_usage(db, group_id, data)

        mock_publish.assert_awaited_once()
        channel = mock_publish.call_args[0][0]
        assert channel == "ai_session", f"Expected 'ai_session' channel for bundle {bundle_id}"


# ---------------------------------------------------------------------------
# Test 7: sync_device_data event carries correct session/usage counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_device_data_event_carries_correct_counts():
    """The device_sync event payload reflects the actual sessions/usage in the request."""
    db = _make_mock_db()
    group_id = uuid.uuid4()
    member_id = uuid.uuid4()

    sessions = [
        DeviceSessionCreate(
            member_id=member_id,
            device_id="device-001",
            device_type="ios",
            started_at=datetime(2026, 3, 21, 8, 0, 0, tzinfo=timezone.utc),
        ),
        DeviceSessionCreate(
            member_id=member_id,
            device_id="device-002",
            device_type="android",
            started_at=datetime(2026, 3, 21, 9, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    usage_records = [
        AppUsageCreate(
            member_id=member_id,
            app_name="TikTok",
            bundle_id="com.zhiliaoapp.musically",
            category="social",
            started_at=datetime(2026, 3, 21, 10, 0, 0, tzinfo=timezone.utc),
            foreground_minutes=20.0,
        ),
    ]
    sync_req = DeviceSyncRequest(
        member_id=member_id,
        device_id="device-001",
        device_type="ios",
        sessions=sessions,
        usage_records=usage_records,
    )

    with patch("src.device_agent.service._publish_intelligence_event", new_callable=AsyncMock) as mock_publish:
        await sync_device_data(db, group_id, sync_req)

    call_args = mock_publish.call_args
    _, event_data = call_args[0]
    assert event_data["sessions_count"] == 2
    assert event_data["usage_count"] == 1
