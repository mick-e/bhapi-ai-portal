"""E2E tests for advanced analytics and trend modelling."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.analytics.service import get_member_baselines, get_trends, get_usage_patterns
from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_trends_empty_group(test_session):
    """Trends for an empty group should return empty data."""
    group, owner_id = await make_test_group(test_session, name="Empty", group_type="family")
    await test_session.flush()

    result = await get_trends(test_session, group.id, days=7)
    assert result["group_id"] == str(group.id)
    assert result["activity"]["direction"] == "stable"
    assert result["risk_events"]["direction"] == "stable"


@pytest.mark.asyncio
async def test_usage_patterns(test_session):
    """Usage patterns should aggregate by hour and platform."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Add some events
    now = datetime.now(timezone.utc)
    for i in range(5):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"s{i}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)

    for i in range(3):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="gemini", session_id=f"g{i}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    result = await get_usage_patterns(test_session, group.id, days=7)
    assert result["by_platform"]["chatgpt"] == 5
    assert result["by_platform"]["gemini"] == 3


@pytest.mark.asyncio
async def test_member_baselines(test_session):
    """Member baselines should be calculated per member."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Add events
    now = datetime.now(timezone.utc)
    for i in range(10):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"s{i}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    baselines = await get_member_baselines(test_session, group.id, days=30)
    assert len(baselines) == 1
    assert baselines[0]["member_name"] == "Child"
    assert baselines[0]["total_events"] == 10
    assert baselines[0]["primary_platform"] == "chatgpt"
