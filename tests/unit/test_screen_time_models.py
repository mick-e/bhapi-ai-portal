"""Unit tests for the screen time module — models and schemas."""

import uuid
from datetime import datetime, time, timezone

import pytest
import pytest_asyncio
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.screen_time.models import ExtensionRequest, ScreenTimeRule, ScreenTimeSchedule
from src.screen_time.schemas import (
    ExtensionRequestCreate,
    ExtensionRequestListResponse,
    ExtensionRequestResponse,
    ScreenTimeRuleCreate,
    ScreenTimeRuleListResponse,
    ScreenTimeRuleResponse,
    ScreenTimeScheduleCreate,
    ScreenTimeScheduleResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def make_uuid() -> uuid.UUID:
    return uuid.uuid4()


async def _create_user_group_member(session: AsyncSession):
    """Create a User, Group, and GroupMember to satisfy FK constraints."""
    owner_id = make_uuid()
    group_id = make_uuid()
    member_id = make_uuid()

    user = User(
        id=owner_id,
        email=f"st-{owner_id.hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehash",
        display_name="Screen Time Test",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(
        id=group_id,
        name="Test Family",
        type="family",
        owner_id=owner_id,
        settings={},
    )
    session.add(group)
    await session.flush()

    member = GroupMember(
        id=member_id,
        group_id=group_id,
        user_id=owner_id,
        role="child",
        display_name="Child",
    )
    session.add(member)
    await session.flush()

    return user, group, member


# ---------------------------------------------------------------------------
# Test 1: ScreenTimeRule model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screen_time_rule_instantiation(test_session: AsyncSession):
    """ScreenTimeRule can be created and queried."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        app_category="social",
        daily_limit_minutes=60,
        age_tier_enforcement="warning_then_block",
        enabled=True,
    )
    test_session.add(rule)
    await test_session.flush()

    result = await test_session.get(ScreenTimeRule, rule.id)
    assert result is not None
    assert result.group_id == group.id
    assert result.member_id == member.id
    assert result.app_category == "social"
    assert result.daily_limit_minutes == 60
    assert result.age_tier_enforcement == "warning_then_block"
    assert result.enabled is True


# ---------------------------------------------------------------------------
# Test 2: ScreenTimeRule default values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screen_time_rule_defaults(test_session: AsyncSession):
    """ScreenTimeRule uses correct default values for optional fields."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=120,
    )
    test_session.add(rule)
    await test_session.flush()

    result = await test_session.get(ScreenTimeRule, rule.id)
    assert result is not None
    assert result.app_category == "all"
    assert result.age_tier_enforcement == "warning_then_block"
    assert result.enabled is True


# ---------------------------------------------------------------------------
# Test 3: ScreenTimeSchedule model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screen_time_schedule_instantiation(test_session: AsyncSession):
    """ScreenTimeSchedule can be created and linked to a rule."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=90,
    )
    test_session.add(rule)
    await test_session.flush()

    schedule = ScreenTimeSchedule(
        id=make_uuid(),
        rule_id=rule.id,
        day_type="weekday",
        blocked_start=time(22, 0),
        blocked_end=time(7, 0),
        description="Bedtime block",
    )
    test_session.add(schedule)
    await test_session.flush()

    result = await test_session.get(ScreenTimeSchedule, schedule.id)
    assert result is not None
    assert result.rule_id == rule.id
    assert result.day_type == "weekday"
    assert result.blocked_start == time(22, 0)
    assert result.blocked_end == time(7, 0)
    assert result.description == "Bedtime block"


# ---------------------------------------------------------------------------
# Test 4: ScreenTimeSchedule without description
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screen_time_schedule_no_description(test_session: AsyncSession):
    """ScreenTimeSchedule allows nullable description."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=45,
    )
    test_session.add(rule)
    await test_session.flush()

    schedule = ScreenTimeSchedule(
        id=make_uuid(),
        rule_id=rule.id,
        day_type="weekend",
        blocked_start=time(23, 0),
        blocked_end=time(8, 0),
    )
    test_session.add(schedule)
    await test_session.flush()

    result = await test_session.get(ScreenTimeSchedule, schedule.id)
    assert result is not None
    assert result.description is None
    assert result.day_type == "weekend"


# ---------------------------------------------------------------------------
# Test 5: ExtensionRequest model instantiation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extension_request_instantiation(test_session: AsyncSession):
    """ExtensionRequest can be created with correct relationships."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=60,
    )
    test_session.add(rule)
    await test_session.flush()

    ext_req = ExtensionRequest(
        id=make_uuid(),
        member_id=member.id,
        rule_id=rule.id,
        requested_minutes=30,
        status="pending",
        requested_at=NOW,
    )
    test_session.add(ext_req)
    await test_session.flush()

    result = await test_session.get(ExtensionRequest, ext_req.id)
    assert result is not None
    assert result.member_id == member.id
    assert result.rule_id == rule.id
    assert result.requested_minutes == 30
    assert result.status == "pending"
    assert result.responded_at is None
    assert result.responded_by is None


# ---------------------------------------------------------------------------
# Test 6: ExtensionRequest with response fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extension_request_with_response(test_session: AsyncSession):
    """ExtensionRequest can be approved with responded_at and responded_by set."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=60,
    )
    test_session.add(rule)
    await test_session.flush()

    ext_req = ExtensionRequest(
        id=make_uuid(),
        member_id=member.id,
        rule_id=rule.id,
        requested_minutes=15,
        status="approved",
        requested_at=NOW,
        responded_at=NOW,
        responded_by=user.id,
    )
    test_session.add(ext_req)
    await test_session.flush()

    result = await test_session.get(ExtensionRequest, ext_req.id)
    assert result is not None
    assert result.status == "approved"
    assert result.responded_at is not None
    assert result.responded_by == user.id


# ---------------------------------------------------------------------------
# Test 7: ScreenTimeRuleCreate schema — app_category validation
# ---------------------------------------------------------------------------


def test_screen_time_rule_create_valid_categories():
    """ScreenTimeRuleCreate accepts all valid app_category values."""
    base = {"member_id": make_uuid(), "daily_limit_minutes": 60}
    for cat in ("social", "games", "education", "entertainment", "productivity", "all"):
        schema = ScreenTimeRuleCreate(**base, app_category=cat)
        assert schema.app_category == cat


def test_screen_time_rule_create_invalid_category():
    """ScreenTimeRuleCreate rejects unknown app_category values."""
    with pytest.raises(PydanticValidationError):
        ScreenTimeRuleCreate(
            member_id=make_uuid(),
            daily_limit_minutes=60,
            app_category="streaming",
        )


# ---------------------------------------------------------------------------
# Test 8: ScreenTimeRuleCreate schema — daily_limit_minutes range
# ---------------------------------------------------------------------------


def test_screen_time_rule_create_limit_bounds():
    """ScreenTimeRuleCreate validates daily_limit_minutes is 1-1440."""
    base = {"member_id": make_uuid()}

    # Valid boundary values
    schema_min = ScreenTimeRuleCreate(**base, daily_limit_minutes=1)
    assert schema_min.daily_limit_minutes == 1

    schema_max = ScreenTimeRuleCreate(**base, daily_limit_minutes=1440)
    assert schema_max.daily_limit_minutes == 1440

    # Zero rejected
    with pytest.raises(PydanticValidationError):
        ScreenTimeRuleCreate(**base, daily_limit_minutes=0)

    # Over 1440 rejected
    with pytest.raises(PydanticValidationError):
        ScreenTimeRuleCreate(**base, daily_limit_minutes=1441)


# ---------------------------------------------------------------------------
# Test 9: ScreenTimeRuleCreate schema — age_tier_enforcement validation
# ---------------------------------------------------------------------------


def test_screen_time_rule_create_enforcement_modes():
    """ScreenTimeRuleCreate accepts all valid age_tier_enforcement values."""
    base = {"member_id": make_uuid(), "daily_limit_minutes": 60}
    for mode in ("hard_block", "warning_then_block", "warning_only"):
        schema = ScreenTimeRuleCreate(**base, age_tier_enforcement=mode)
        assert schema.age_tier_enforcement == mode


def test_screen_time_rule_create_invalid_enforcement():
    """ScreenTimeRuleCreate rejects unknown enforcement modes."""
    with pytest.raises(PydanticValidationError):
        ScreenTimeRuleCreate(
            member_id=make_uuid(),
            daily_limit_minutes=60,
            age_tier_enforcement="soft_block",
        )


# ---------------------------------------------------------------------------
# Test 10: ScreenTimeScheduleCreate schema — day_type validation
# ---------------------------------------------------------------------------


def test_screen_time_schedule_create_valid_day_types():
    """ScreenTimeScheduleCreate accepts weekday, weekend, and custom."""
    base = {
        "rule_id": make_uuid(),
        "blocked_start": time(22, 0),
        "blocked_end": time(7, 0),
    }
    for day_type in ("weekday", "weekend", "custom"):
        schema = ScreenTimeScheduleCreate(**base, day_type=day_type)
        assert schema.day_type == day_type


def test_screen_time_schedule_create_invalid_day_type():
    """ScreenTimeScheduleCreate rejects unknown day_type values."""
    with pytest.raises(PydanticValidationError):
        ScreenTimeScheduleCreate(
            rule_id=make_uuid(),
            day_type="holiday",
            blocked_start=time(22, 0),
            blocked_end=time(7, 0),
        )


# ---------------------------------------------------------------------------
# Test 11: ExtensionRequestCreate schema — requested_minutes range
# ---------------------------------------------------------------------------


def test_extension_request_create_minutes_bounds():
    """ExtensionRequestCreate validates requested_minutes is 1-120."""
    base = {"member_id": make_uuid(), "rule_id": make_uuid()}

    # Valid boundary values
    schema_min = ExtensionRequestCreate(**base, requested_minutes=1)
    assert schema_min.requested_minutes == 1

    schema_max = ExtensionRequestCreate(**base, requested_minutes=120)
    assert schema_max.requested_minutes == 120

    # Zero rejected
    with pytest.raises(PydanticValidationError):
        ExtensionRequestCreate(**base, requested_minutes=0)

    # Over 120 rejected
    with pytest.raises(PydanticValidationError):
        ExtensionRequestCreate(**base, requested_minutes=121)


# ---------------------------------------------------------------------------
# Test 12: ExtensionRequestListResponse pagination schema
# ---------------------------------------------------------------------------


def test_extension_request_list_response_structure():
    """ExtensionRequestListResponse correctly structures paginated data."""
    entry = ExtensionRequestResponse(
        id=make_uuid(),
        member_id=make_uuid(),
        rule_id=make_uuid(),
        requested_minutes=30,
        status="pending",
        requested_at=NOW,
        responded_at=None,
        responded_by=None,
        created_at=NOW,
    )
    response = ExtensionRequestListResponse(
        items=[entry],
        total=5,
        has_more=False,
    )
    assert response.total == 5
    assert response.has_more is False
    assert len(response.items) == 1
    assert response.items[0].requested_minutes == 30
    assert response.items[0].status == "pending"


# ---------------------------------------------------------------------------
# Test 13: ScreenTimeRuleListResponse pagination schema
# ---------------------------------------------------------------------------


def test_screen_time_rule_list_response_structure():
    """ScreenTimeRuleListResponse correctly structures rule lists."""
    rule_resp = ScreenTimeRuleResponse(
        id=make_uuid(),
        group_id=make_uuid(),
        member_id=make_uuid(),
        app_category="games",
        daily_limit_minutes=90,
        age_tier_enforcement="hard_block",
        enabled=True,
        created_at=NOW,
    )
    list_resp = ScreenTimeRuleListResponse(items=[rule_resp], total=1)
    assert list_resp.total == 1
    assert list_resp.items[0].app_category == "games"
    assert list_resp.items[0].age_tier_enforcement == "hard_block"


# ---------------------------------------------------------------------------
# Test 14: ScreenTimeScheduleResponse from_attributes
# ---------------------------------------------------------------------------


def test_screen_time_schedule_response_schema():
    """ScreenTimeScheduleResponse serialises schedule correctly."""
    resp = ScreenTimeScheduleResponse(
        id=make_uuid(),
        rule_id=make_uuid(),
        day_type="weekend",
        blocked_start=time(21, 30),
        blocked_end=time(8, 0),
        description="Weekend bedtime",
        created_at=NOW,
    )
    assert resp.day_type == "weekend"
    assert resp.blocked_start == time(21, 30)
    assert resp.description == "Weekend bedtime"


# ---------------------------------------------------------------------------
# Test 15: Multiple schedules per rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_schedules_per_rule(test_session: AsyncSession):
    """A single rule can have multiple schedules for different day types."""
    user, group, member = await _create_user_group_member(test_session)

    rule = ScreenTimeRule(
        id=make_uuid(),
        group_id=group.id,
        member_id=member.id,
        daily_limit_minutes=120,
    )
    test_session.add(rule)
    await test_session.flush()

    schedules = [
        ScreenTimeSchedule(
            id=make_uuid(),
            rule_id=rule.id,
            day_type="weekday",
            blocked_start=time(22, 0),
            blocked_end=time(7, 0),
        ),
        ScreenTimeSchedule(
            id=make_uuid(),
            rule_id=rule.id,
            day_type="weekend",
            blocked_start=time(23, 0),
            blocked_end=time(9, 0),
        ),
    ]
    for s in schedules:
        test_session.add(s)
    await test_session.flush()

    for s in schedules:
        result = await test_session.get(ScreenTimeSchedule, s.id)
        assert result is not None
        assert result.rule_id == rule.id
