"""Integration tests: device agent AppUsageRecord data → screen time evaluation pipeline."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.device_agent.models import AppUsageRecord
from src.groups.models import Group, GroupMember
from src.screen_time.service import create_rule, evaluate_usage

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def pipeline_data(test_session: AsyncSession):
    """Create a parent user, family group, and a preteen child member (~11 yrs)."""
    user = User(
        id=uuid.uuid4(),
        email=f"pipeline-parent-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Pipeline Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Pipeline Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    # Preteen child, age ~11
    child = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Pipeline Child",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 11, 6, 15, tzinfo=timezone.utc
        ),
    )
    test_session.add(child)
    await test_session.flush()

    return {"user": user, "group": group, "child": child}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _today_dt() -> datetime:
    """Return a datetime anchored to today at 08:00 UTC (safely within the day window)."""
    today = datetime.now(timezone.utc).date()
    return datetime(today.year, today.month, today.day, 8, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_device_usage_triggers_block(
    test_session: AsyncSession, pipeline_data: dict
):
    """90 min of 'games' usage against a 60-min limit → block at 150%."""
    child = pipeline_data["child"]
    group = pipeline_data["group"]

    # Create rule: 60-min daily limit on games
    await create_rule(
        test_session,
        group_id=group.id,
        member_id=child.id,
        app_category="games",
        daily_limit_minutes=60,
        age_tier_enforcement="warning_then_block",
    )

    # Insert AppUsageRecord with 90 minutes of games today
    record = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="Roblox",
        bundle_id="com.roblox.robloxmobile",
        category="games",
        started_at=_today_dt(),
        foreground_minutes=90.0,
    )
    test_session.add(record)
    await test_session.flush()

    results = await evaluate_usage(test_session, child.id)

    assert len(results) == 1
    result = results[0]
    assert result["category"] == "games"
    assert result["used_minutes"] == 90.0
    assert result["limit_minutes"] == 60
    assert result["percent"] == 150.0
    assert result["enforcement_action"] == "block"


@pytest.mark.asyncio
async def test_device_usage_under_limit_allows(
    test_session: AsyncSession, pipeline_data: dict
):
    """30 min of 'social' usage against a 120-min limit → allow at 25%."""
    child = pipeline_data["child"]
    group = pipeline_data["group"]

    await create_rule(
        test_session,
        group_id=group.id,
        member_id=child.id,
        app_category="social",
        daily_limit_minutes=120,
        age_tier_enforcement="warning_then_block",
    )

    record = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="BeReal",
        bundle_id="com.bereal.ft",
        category="social",
        started_at=_today_dt(),
        foreground_minutes=30.0,
    )
    test_session.add(record)
    await test_session.flush()

    results = await evaluate_usage(test_session, child.id)

    assert len(results) == 1
    result = results[0]
    assert result["category"] == "social"
    assert result["used_minutes"] == 30.0
    assert result["limit_minutes"] == 120
    assert result["percent"] == 25.0
    assert result["enforcement_action"] == "allow"


@pytest.mark.asyncio
async def test_device_usage_near_limit_warns(
    test_session: AsyncSession, pipeline_data: dict
):
    """85 min of 'entertainment' usage against a 100-min limit → warn at 85%."""
    child = pipeline_data["child"]
    group = pipeline_data["group"]

    await create_rule(
        test_session,
        group_id=group.id,
        member_id=child.id,
        app_category="entertainment",
        daily_limit_minutes=100,
        age_tier_enforcement="warning_then_block",
    )

    record = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="YouTube",
        bundle_id="com.google.ios.youtube",
        category="entertainment",
        started_at=_today_dt(),
        foreground_minutes=85.0,
    )
    test_session.add(record)
    await test_session.flush()

    results = await evaluate_usage(test_session, child.id)

    assert len(results) == 1
    result = results[0]
    assert result["category"] == "entertainment"
    assert result["used_minutes"] == 85.0
    assert result["limit_minutes"] == 100
    assert result["percent"] == 85.0
    assert result["enforcement_action"] == "warn"


@pytest.mark.asyncio
async def test_no_rules_returns_empty(
    test_session: AsyncSession, pipeline_data: dict
):
    """A child with no active rules returns an empty evaluation list."""
    child = pipeline_data["child"]
    group = pipeline_data["group"]

    # Insert usage data but no rules
    record = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="Minecraft",
        bundle_id="com.mojang.minecraftpe",
        category="games",
        started_at=_today_dt(),
        foreground_minutes=45.0,
    )
    test_session.add(record)
    await test_session.flush()

    results = await evaluate_usage(test_session, child.id)

    assert results == []
