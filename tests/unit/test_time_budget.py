"""Unit tests for time budget — budget calc, timezone, weekend detection."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from src.blocking.time_budget import (
    _is_weekend,
    _get_today_for_tz,
    check_time_budget,
    record_session_time,
    set_time_budget,
    get_time_budget,
    get_usage_history,
    TimeBudget,
    TimeBudgetUsage,
)
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_is_weekend_saturday():
    """Saturday should be weekend."""
    # 2026-03-14 is a Saturday
    assert _is_weekend(date(2026, 3, 14)) is True


@pytest.mark.asyncio
async def test_is_weekend_sunday():
    """Sunday should be weekend."""
    # 2026-03-15 is a Sunday
    assert _is_weekend(date(2026, 3, 15)) is True


@pytest.mark.asyncio
async def test_is_weekend_weekday():
    """Monday should not be weekend."""
    # 2026-03-16 is a Monday
    assert _is_weekend(date(2026, 3, 16)) is False


@pytest.mark.asyncio
async def test_get_today_for_tz_utc():
    """UTC timezone should return today's date."""
    today = _get_today_for_tz("UTC")
    assert isinstance(today, date)


@pytest.mark.asyncio
async def test_get_today_for_tz_invalid_fallback():
    """Invalid timezone falls back to UTC."""
    today = _get_today_for_tz("Invalid/Zone")
    assert isinstance(today, date)


@pytest.mark.asyncio
async def test_set_time_budget_creates_new(test_session):
    """Setting time budget for the first time creates it."""
    group, owner_id = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    budget = await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=45, weekend_minutes=90,
    )
    assert budget.weekday_minutes == 45
    assert budget.weekend_minutes == 90
    assert budget.enabled is True


@pytest.mark.asyncio
async def test_set_time_budget_updates_existing(test_session):
    """Setting time budget again updates existing."""
    group, owner_id = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(test_session, group.id, member.id, weekday_minutes=60)
    budget = await set_time_budget(test_session, group.id, member.id, weekday_minutes=30)
    assert budget.weekday_minutes == 30


@pytest.mark.asyncio
async def test_check_time_budget_no_budget(test_session):
    """No budget config returns disabled status."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    result = await check_time_budget(test_session, group.id, member.id)
    assert result["enabled"] is False
    assert result["exceeded"] is False


@pytest.mark.asyncio
async def test_check_time_budget_with_usage(test_session):
    """Check budget with recorded usage."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(test_session, group.id, member.id, weekday_minutes=60, weekend_minutes=120)
    await record_session_time(test_session, group.id, member.id, 30)

    result = await check_time_budget(test_session, group.id, member.id)
    assert result["enabled"] is True
    assert result["minutes_used"] == 30
    assert result["remaining"] > 0


@pytest.mark.asyncio
async def test_record_session_time_cumulative(test_session):
    """Recording session time is cumulative for the same day."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(test_session, group.id, member.id, weekday_minutes=60)
    await record_session_time(test_session, group.id, member.id, 20)
    usage = await record_session_time(test_session, group.id, member.id, 25)
    assert usage.minutes_used == 45


@pytest.mark.asyncio
async def test_record_session_time_exceeded(test_session):
    """Exceeding budget sets exceeded flag."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(test_session, group.id, member.id, weekday_minutes=30, weekend_minutes=30)
    usage = await record_session_time(test_session, group.id, member.id, 35)
    assert usage.exceeded is True
    assert usage.exceeded_at is not None


@pytest.mark.asyncio
async def test_record_session_time_negative_rejected(test_session):
    """Negative minutes should be rejected."""
    from src.exceptions import ValidationError

    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(ValidationError):
        await record_session_time(test_session, group.id, member.id, -5)


@pytest.mark.asyncio
async def test_set_time_budget_invalid_reset_hour(test_session):
    """Invalid reset hour should be rejected."""
    from src.exceptions import ValidationError

    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(ValidationError):
        await set_time_budget(test_session, group.id, member.id, reset_hour=25)


@pytest.mark.asyncio
async def test_get_usage_history_empty(test_session):
    """Usage history returns empty list when no data."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    history = await get_usage_history(test_session, group.id, member.id)
    assert history == []


@pytest.mark.asyncio
async def test_warn_threshold(test_session):
    """Warn flag is set when usage exceeds warn_at_percent."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # 100 min budget, 75% warn = warn at 75 min
    await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=100, weekend_minutes=100, warn_at_percent=75,
    )
    await record_session_time(test_session, group.id, member.id, 80)

    result = await check_time_budget(test_session, group.id, member.id)
    assert result["warn"] is True
    assert result["exceeded"] is False
