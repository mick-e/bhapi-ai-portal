"""E2E tests for multi-device correlation (F12).

Tests multi-device session aggregation.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tests.conftest import make_test_group
from src.capture.models import CaptureEvent, DeviceRegistration
from src.capture.service import get_member_session_summary
from src.groups.models import GroupMember


@pytest.mark.asyncio
async def test_empty_session_summary(test_session):
    """No events returns zero totals."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    summary = await get_member_session_summary(test_session, group.id, child.id)
    assert summary["total_minutes"] == 0
    assert summary["session_count"] == 0
    assert summary["device_breakdown"] == []
    assert summary["platform_breakdown"] == []


@pytest.mark.asyncio
async def test_single_device_summary(test_session):
    """Summary for a single device with events."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    device = DeviceRegistration(
        id=uuid4(), group_id=group.id, member_id=child.id,
        device_name="Laptop", setup_code="CODE01",
    )
    test_session.add(device)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    for i in range(3):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=child.id,
            platform="chatgpt", session_id=f"sess-{i}",
            event_type="prompt", timestamp=now,
            risk_processed=False, source_channel="extension",
            device_id=device.id,
        )
        test_session.add(event)
    await test_session.flush()

    summary = await get_member_session_summary(test_session, group.id, child.id, now.date())
    assert summary["total_minutes"] == 6  # 3 events * 2 min
    assert summary["session_count"] == 3
    assert len(summary["device_breakdown"]) == 1
    assert summary["device_breakdown"][0]["device_name"] == "Laptop"
    assert len(summary["platform_breakdown"]) == 1
    assert summary["platform_breakdown"][0]["platform"] == "chatgpt"


@pytest.mark.asyncio
async def test_multi_device_summary(test_session):
    """Summary aggregates across multiple devices."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    device1 = DeviceRegistration(
        id=uuid4(), group_id=group.id, member_id=child.id,
        device_name="Laptop", setup_code="CODE02",
    )
    device2 = DeviceRegistration(
        id=uuid4(), group_id=group.id, member_id=child.id,
        device_name="iPad", setup_code="CODE03",
    )
    test_session.add(device1)
    test_session.add(device2)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    # 2 events on device 1 (chatgpt)
    for i in range(2):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=child.id,
            platform="chatgpt", session_id=f"laptop-sess-{i}",
            event_type="prompt", timestamp=now,
            risk_processed=False, source_channel="extension",
            device_id=device1.id,
        )
        test_session.add(event)

    # 3 events on device 2 (gemini)
    for i in range(3):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=child.id,
            platform="gemini", session_id=f"ipad-sess-{i}",
            event_type="prompt", timestamp=now,
            risk_processed=False, source_channel="extension",
            device_id=device2.id,
        )
        test_session.add(event)
    await test_session.flush()

    summary = await get_member_session_summary(test_session, group.id, child.id, now.date())
    assert summary["total_minutes"] == 10  # 5 events * 2 min
    assert summary["session_count"] == 5
    assert len(summary["device_breakdown"]) == 2

    device_names = {d["device_name"] for d in summary["device_breakdown"]}
    assert "Laptop" in device_names
    assert "iPad" in device_names

    platform_names = {p["platform"] for p in summary["platform_breakdown"]}
    assert "chatgpt" in platform_names
    assert "gemini" in platform_names


@pytest.mark.asyncio
async def test_events_without_device_grouped(test_session):
    """Events without a device_id are grouped under 'unknown'."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    event = CaptureEvent(
        id=uuid4(), group_id=group.id, member_id=child.id,
        platform="claude", session_id="no-dev-sess",
        event_type="prompt", timestamp=now,
        risk_processed=False, source_channel="api",
        device_id=None,
    )
    test_session.add(event)
    await test_session.flush()

    summary = await get_member_session_summary(test_session, group.id, child.id, now.date())
    assert summary["total_minutes"] == 2
    assert len(summary["device_breakdown"]) == 1
    assert summary["device_breakdown"][0]["device_id"] == "unknown"


@pytest.mark.asyncio
async def test_date_filtering(test_session):
    """Summary only includes events from the target date."""
    from datetime import timedelta, date as dt_date

    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    # Event yesterday
    event1 = CaptureEvent(
        id=uuid4(), group_id=group.id, member_id=child.id,
        platform="chatgpt", session_id="yest-sess",
        event_type="prompt", timestamp=yesterday,
        risk_processed=False, source_channel="extension",
    )
    # Event today
    event2 = CaptureEvent(
        id=uuid4(), group_id=group.id, member_id=child.id,
        platform="chatgpt", session_id="today-sess",
        event_type="prompt", timestamp=now,
        risk_processed=False, source_channel="extension",
    )
    test_session.add(event1)
    test_session.add(event2)
    await test_session.flush()

    # Query for today only
    summary = await get_member_session_summary(test_session, group.id, child.id, now.date())
    assert summary["session_count"] == 1

    # Query for yesterday
    summary_y = await get_member_session_summary(test_session, group.id, child.id, yesterday.date())
    assert summary_y["session_count"] == 1
