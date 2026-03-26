"""Unit tests for the screen time service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import AgeTier
from src.auth.models import User
from src.device_agent.models import AppUsageRecord, ScreenTimeRecord
from src.exceptions import NotFoundError, RateLimitError, ValidationError
from src.groups.models import Group, GroupMember
from src.screen_time.models import ExtensionRequest
from src.screen_time.service import (
    EXTENSION_DAILY_LIMITS,
    EXTENSION_EXPIRY_MINUTES,
    create_extension_request,
    create_rule,
    create_schedule,
    delete_rule,
    evaluate_usage,
    get_rules,
    get_schedules,
    get_weekly_report,
    respond_to_extension,
    update_rule,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def st_data(test_session: AsyncSession):
    """Create a group, parent user, and child member for screen time tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"st-parent-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="ST Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(), name="ST Family", type="family", owner_id=user.id
    )
    test_session.add(group)
    await test_session.flush()

    # Preteen child (age ~11)
    preteen = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Preteen Child",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 11, 6, 15, tzinfo=timezone.utc
        ),
    )
    # Young child (age ~7)
    young = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Young Child",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 7, 3, 10, tzinfo=timezone.utc
        ),
    )
    # Teen child (age ~14)
    teen = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Teen Child",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 14, 9, 5, tzinfo=timezone.utc
        ),
    )
    test_session.add_all([preteen, young, teen])
    await test_session.flush()

    return {
        "user": user,
        "group": group,
        "preteen": preteen,
        "young": young,
        "teen": teen,
    }


# ---------------------------------------------------------------------------
# Rule CRUD Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule(test_session: AsyncSession, st_data):
    """Create a screen time rule."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="social",
        daily_limit_minutes=60,
        age_tier_enforcement="hard_block",
        enabled=True,
    )
    assert rule.id is not None
    assert rule.app_category == "social"
    assert rule.daily_limit_minutes == 60
    assert rule.age_tier_enforcement == "hard_block"
    assert rule.enabled is True


@pytest.mark.asyncio
async def test_create_rule_defaults(test_session: AsyncSession, st_data):
    """Create a rule with defaults."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="all",
        daily_limit_minutes=120,
    )
    assert rule.age_tier_enforcement == "warning_then_block"
    assert rule.enabled is True


@pytest.mark.asyncio
async def test_get_rules_empty(test_session: AsyncSession, st_data):
    """Get rules returns empty list when none exist."""
    rules = await get_rules(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
    )
    assert rules == []


@pytest.mark.asyncio
async def test_get_rules_returns_member_rules(test_session: AsyncSession, st_data):
    """get_rules returns only the specified member's rules."""
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["young"].id,
        app_category="social",
        daily_limit_minutes=10,
    )
    rules = await get_rules(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
    )
    assert len(rules) == 1
    assert rules[0].app_category == "games"


@pytest.mark.asyncio
async def test_update_rule(test_session: AsyncSession, st_data):
    """Update an existing rule."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="social",
        daily_limit_minutes=60,
    )
    updated = await update_rule(
        test_session,
        rule_id=rule.id,
        data={"daily_limit_minutes": 90, "enabled": False},
    )
    assert updated.daily_limit_minutes == 90
    assert updated.enabled is False


@pytest.mark.asyncio
async def test_update_rule_not_found(test_session: AsyncSession):
    """Update non-existent rule raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await update_rule(test_session, rule_id=uuid.uuid4(), data={"enabled": False})


@pytest.mark.asyncio
async def test_delete_rule(test_session: AsyncSession, st_data):
    """Delete a rule."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="social",
        daily_limit_minutes=60,
    )
    await delete_rule(test_session, rule_id=rule.id)
    rules = await get_rules(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
    )
    assert rules == []


@pytest.mark.asyncio
async def test_delete_rule_not_found(test_session: AsyncSession):
    """Delete non-existent rule raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await delete_rule(test_session, rule_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Schedule Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule(test_session: AsyncSession, st_data):
    """Create a schedule attached to a rule."""
    from datetime import time
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=45,
    )
    schedule = await create_schedule(
        test_session,
        rule_id=rule.id,
        day_type="weekday",
        blocked_start=time(22, 0),
        blocked_end=time(8, 0),
        description="Bedtime block",
    )
    assert schedule.rule_id == rule.id
    assert schedule.day_type == "weekday"
    assert schedule.description == "Bedtime block"


@pytest.mark.asyncio
async def test_create_schedule_invalid_rule(test_session: AsyncSession):
    """Create schedule with non-existent rule raises NotFoundError."""
    from datetime import time
    with pytest.raises(NotFoundError):
        await create_schedule(
            test_session,
            rule_id=uuid.uuid4(),
            day_type="weekday",
            blocked_start=time(22, 0),
            blocked_end=time(8, 0),
        )


@pytest.mark.asyncio
async def test_get_schedules(test_session: AsyncSession, st_data):
    """Get schedules for a rule."""
    from datetime import time
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=45,
    )
    await create_schedule(
        test_session, rule_id=rule.id, day_type="weekday",
        blocked_start=time(22, 0), blocked_end=time(8, 0),
    )
    await create_schedule(
        test_session, rule_id=rule.id, day_type="weekend",
        blocked_start=time(23, 0), blocked_end=time(9, 0),
    )
    schedules = await get_schedules(test_session, rule_id=rule.id)
    assert len(schedules) == 2


# ---------------------------------------------------------------------------
# Extension Request Rate Limiting Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extension_rate_limit_young_is_zero(test_session: AsyncSession, st_data):
    """Young children (5-9) cannot request extensions."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["young"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    with pytest.raises(ValidationError, match="not available for this age group"):
        await create_extension_request(
            test_session,
            member_id=st_data["young"].id,
            rule_id=rule.id,
            requested_minutes=15,
        )


@pytest.mark.asyncio
async def test_extension_rate_limit_preteen_two_per_day(test_session: AsyncSession, st_data):
    """Preteen children can make 2 extension requests per day."""
    assert EXTENSION_DAILY_LIMITS[AgeTier.PRETEEN] == 2
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    # First request — OK
    req1 = await create_extension_request(
        test_session,
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
    )
    assert req1.status == "pending"
    await test_session.flush()

    # Second request — OK
    req2 = await create_extension_request(
        test_session,
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
    )
    assert req2.status == "pending"
    await test_session.flush()

    # Third request — should fail
    with pytest.raises(RateLimitError, match="Daily extension request limit"):
        await create_extension_request(
            test_session,
            member_id=st_data["preteen"].id,
            rule_id=rule.id,
            requested_minutes=15,
        )


@pytest.mark.asyncio
async def test_extension_rate_limit_teen_five_per_day(test_session: AsyncSession, st_data):
    """Teen children (13-15) can make 5 extension requests per day."""
    assert EXTENSION_DAILY_LIMITS[AgeTier.TEEN] == 5
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["teen"].id,
        app_category="social",
        daily_limit_minutes=60,
    )
    for _ in range(5):
        await create_extension_request(
            test_session,
            member_id=st_data["teen"].id,
            rule_id=rule.id,
            requested_minutes=10,
        )
        await test_session.flush()

    # Sixth request — should fail
    with pytest.raises(RateLimitError):
        await create_extension_request(
            test_session,
            member_id=st_data["teen"].id,
            rule_id=rule.id,
            requested_minutes=10,
        )


# ---------------------------------------------------------------------------
# Auto-deny expired requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_auto_denies_expired(test_session: AsyncSession, st_data):
    """respond_to_extension auto-denies requests older than EXTENSION_EXPIRY_MINUTES."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    # Create a request manually with old timestamp
    old_time = datetime.now(timezone.utc) - timedelta(minutes=EXTENSION_EXPIRY_MINUTES + 1)
    req = ExtensionRequest(
        id=uuid.uuid4(),
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
        status="pending",
        requested_at=old_time,
    )
    test_session.add(req)
    await test_session.flush()

    result = await respond_to_extension(
        test_session,
        request_id=req.id,
        parent_id=st_data["user"].id,
        approved=True,
    )
    # Even though parent tried to approve, it expired
    assert result.status == "expired"


@pytest.mark.asyncio
async def test_respond_approve_valid_request(test_session: AsyncSession, st_data):
    """Approve a valid (non-expired) extension request."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    req = await create_extension_request(
        test_session,
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
    )
    await test_session.flush()

    result = await respond_to_extension(
        test_session,
        request_id=req.id,
        parent_id=st_data["user"].id,
        approved=True,
    )
    assert result.status == "approved"
    assert result.responded_by == st_data["user"].id


@pytest.mark.asyncio
async def test_respond_deny_request(test_session: AsyncSession, st_data):
    """Deny a valid extension request."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    req = await create_extension_request(
        test_session,
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
    )
    await test_session.flush()

    result = await respond_to_extension(
        test_session,
        request_id=req.id,
        parent_id=st_data["user"].id,
        approved=False,
    )
    assert result.status == "denied"


@pytest.mark.asyncio
async def test_respond_already_responded_raises(test_session: AsyncSession, st_data):
    """Responding to an already-resolved request raises ValidationError."""
    rule = await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
    )
    req = await create_extension_request(
        test_session,
        member_id=st_data["preteen"].id,
        rule_id=rule.id,
        requested_minutes=15,
    )
    await test_session.flush()

    await respond_to_extension(
        test_session,
        request_id=req.id,
        parent_id=st_data["user"].id,
        approved=True,
    )
    await test_session.flush()

    with pytest.raises(ValidationError, match="already approved"):
        await respond_to_extension(
            test_session,
            request_id=req.id,
            parent_id=st_data["user"].id,
            approved=False,
        )


# ---------------------------------------------------------------------------
# evaluate_usage Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_usage_empty(test_session: AsyncSession, st_data):
    """evaluate_usage returns empty list when no rules exist."""
    result = await evaluate_usage(test_session, member_id=st_data["preteen"].id)
    assert result == []


@pytest.mark.asyncio
async def test_evaluate_usage_allow_under_limit(test_session: AsyncSession, st_data):
    """evaluate_usage returns allow when usage is well under limit."""
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="social",
        daily_limit_minutes=120,
        age_tier_enforcement="hard_block",
    )
    await test_session.flush()

    # Add 30 minutes of social usage today
    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=st_data["preteen"].id,
        group_id=st_data["group"].id,
        app_name="Instagram",
        bundle_id="com.instagram.android",
        category="social",
        started_at=now,
        foreground_minutes=30.0,
    )
    test_session.add(usage)
    await test_session.flush()

    result = await evaluate_usage(test_session, member_id=st_data["preteen"].id)
    assert len(result) == 1
    eval_item = result[0]
    assert eval_item["enforcement_action"] == "allow"
    assert eval_item["used_minutes"] == 30.0
    assert eval_item["limit_minutes"] == 120


@pytest.mark.asyncio
async def test_evaluate_usage_warn_near_limit(test_session: AsyncSession, st_data):
    """evaluate_usage returns warn when usage is 80%+ of limit."""
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="social",
        daily_limit_minutes=100,
        age_tier_enforcement="warning_then_block",
    )
    await test_session.flush()

    # Add 85 minutes — 85% of limit
    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=st_data["preteen"].id,
        group_id=st_data["group"].id,
        app_name="TikTok",
        bundle_id="com.zhiliaoapp.musically",
        category="social",
        started_at=now,
        foreground_minutes=85.0,
    )
    test_session.add(usage)
    await test_session.flush()

    result = await evaluate_usage(test_session, member_id=st_data["preteen"].id)
    assert result[0]["enforcement_action"] == "warn"


@pytest.mark.asyncio
async def test_evaluate_usage_block_at_limit(test_session: AsyncSession, st_data):
    """evaluate_usage returns block when usage meets/exceeds limit (hard_block)."""
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=60,
        age_tier_enforcement="hard_block",
    )
    await test_session.flush()

    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=st_data["preteen"].id,
        group_id=st_data["group"].id,
        app_name="Minecraft",
        bundle_id="com.mojang.minecraft",
        category="games",
        started_at=now,
        foreground_minutes=65.0,
    )
    test_session.add(usage)
    await test_session.flush()

    result = await evaluate_usage(test_session, member_id=st_data["preteen"].id)
    assert result[0]["enforcement_action"] == "block"
    assert result[0]["percent"] > 100


@pytest.mark.asyncio
async def test_evaluate_usage_warning_only_never_blocks(test_session: AsyncSession, st_data):
    """warning_only enforcement never produces block action."""
    await create_rule(
        test_session,
        group_id=st_data["group"].id,
        member_id=st_data["preteen"].id,
        app_category="games",
        daily_limit_minutes=30,
        age_tier_enforcement="warning_only",
    )
    await test_session.flush()

    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=st_data["preteen"].id,
        group_id=st_data["group"].id,
        app_name="Roblox",
        bundle_id="com.roblox.client",
        category="games",
        started_at=now,
        foreground_minutes=120.0,
    )
    test_session.add(usage)
    await test_session.flush()

    result = await evaluate_usage(test_session, member_id=st_data["preteen"].id)
    assert result[0]["enforcement_action"] == "warn"


# ---------------------------------------------------------------------------
# Weekly Report Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weekly_report_empty(test_session: AsyncSession, st_data):
    """Weekly report with no data returns zeros."""
    report = await get_weekly_report(test_session, member_id=st_data["preteen"].id)
    assert report["total_minutes"] == 0.0
    assert report["days_with_data"] == 0
    assert report["daily_totals"] == []


@pytest.mark.asyncio
async def test_weekly_report_aggregates_days(test_session: AsyncSession, st_data):
    """Weekly report aggregates last 7 days of ScreenTimeRecord data."""
    today = datetime.now(timezone.utc).date()

    for i in range(3):
        target_date = today - timedelta(days=i)
        rec = ScreenTimeRecord(
            id=uuid.uuid4(),
            member_id=st_data["preteen"].id,
            group_id=st_data["group"].id,
            date=target_date,
            total_minutes=60.0 + i * 10,
            category_breakdown={"social": 30.0, "games": 30.0 + i * 10},
            pickups=5,
        )
        test_session.add(rec)

    await test_session.flush()

    report = await get_weekly_report(test_session, member_id=st_data["preteen"].id)
    assert report["days_with_data"] == 3
    assert report["total_minutes"] == 60.0 + 70.0 + 80.0
    assert "social" in report["category_totals"]
    assert report["daily_average_minutes"] == report["total_minutes"] / 3
