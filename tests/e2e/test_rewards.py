"""E2E tests for AI Usage Allowance Rewards (F14).

Tests trigger evaluation, reward listing, and extra time budget integration.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from tests.conftest import make_test_group
from src.groups.models import GroupMember
from src.groups.rewards import (
    BADGE_NAMES,
    REWARD_TRIGGERS,
    check_and_award_rewards,
    get_extra_time_minutes,
    list_rewards,
    redeem_reward,
    Reward,
)
from src.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_no_rewards_initially(test_session):
    """A new member has no rewards."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    rewards = await list_rewards(test_session, group.id, child.id)
    assert len(rewards) == 0


@pytest.mark.asyncio
async def test_extra_time_zero_initially(test_session):
    """Extra time is 0 for a new member."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    minutes = await get_extra_time_minutes(test_session, group.id, child.id)
    assert minutes == 0


@pytest.mark.asyncio
async def test_manual_reward_creation_and_listing(test_session):
    """Create a reward manually and verify listing."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    reward = Reward(
        id=uuid4(),
        group_id=group.id,
        member_id=child.id,
        reward_type="extra_time",
        trigger="literacy_module_complete",
        trigger_description="Completed an AI literacy module",
        value=15,
        earned_at=now,
        expires_at=now + timedelta(days=30),
        redeemed=False,
    )
    test_session.add(reward)
    await test_session.flush()

    rewards = await list_rewards(test_session, group.id, child.id)
    assert len(rewards) == 1
    assert rewards[0].reward_type == "extra_time"
    assert rewards[0].value == 15


@pytest.mark.asyncio
async def test_extra_time_calculation(test_session):
    """Extra time sums unredeemed, non-expired extra_time rewards."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    # Active reward: 15 min
    r1 = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="extra_time", trigger="literacy_module_complete",
        trigger_description="Test", value=15, earned_at=now,
        expires_at=now + timedelta(days=30), redeemed=False,
    )
    # Another active reward: 30 min
    r2 = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="extra_time", trigger="safety_score_above_80",
        trigger_description="Test", value=30, earned_at=now,
        expires_at=now + timedelta(days=30), redeemed=False,
    )
    # Redeemed reward (should not count): 20 min
    r3 = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="extra_time", trigger="agreement_compliance_week",
        trigger_description="Test", value=20, earned_at=now,
        expires_at=now + timedelta(days=30), redeemed=True,
    )
    # Badge (should not count)
    r4 = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="badge", trigger="week_no_high_risk",
        trigger_description="Test", value=1, earned_at=now,
        expires_at=None, redeemed=False,
    )
    test_session.add_all([r1, r2, r3, r4])
    await test_session.flush()

    minutes = await get_extra_time_minutes(test_session, group.id, child.id)
    assert minutes == 45  # 15 + 30 only


@pytest.mark.asyncio
async def test_redeem_reward(test_session):
    """Redeeming a reward marks it as redeemed."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    reward = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="extra_time", trigger="literacy_module_complete",
        trigger_description="Test", value=15, earned_at=now,
        expires_at=now + timedelta(days=30), redeemed=False,
    )
    test_session.add(reward)
    await test_session.flush()

    redeemed = await redeem_reward(test_session, reward.id)
    assert redeemed.redeemed is True

    # Extra time should now be 0
    minutes = await get_extra_time_minutes(test_session, group.id, child.id)
    assert minutes == 0


@pytest.mark.asyncio
async def test_redeem_nonexistent_reward(test_session):
    """Redeeming a non-existent reward raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await redeem_reward(test_session, uuid4())


@pytest.mark.asyncio
async def test_check_and_award_no_double_award(test_session):
    """Same trigger not awarded twice in the same week."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    # Pre-create a recent reward for the same trigger
    now = datetime.now(timezone.utc)
    existing = Reward(
        id=uuid4(), group_id=group.id, member_id=child.id,
        reward_type="badge", trigger="week_no_high_risk",
        trigger_description="Already earned", value=1,
        earned_at=now - timedelta(days=2),
        expires_at=None, redeemed=False,
    )
    test_session.add(existing)
    await test_session.flush()

    # Check should not re-award week_no_high_risk
    awarded = await check_and_award_rewards(test_session, group.id, child.id)
    trigger_names = [r.trigger for r in awarded]
    assert "week_no_high_risk" not in trigger_names


@pytest.mark.asyncio
async def test_reward_triggers_config(test_session):
    """Verify REWARD_TRIGGERS and BADGE_NAMES are properly defined."""
    assert "literacy_module_complete" in REWARD_TRIGGERS
    assert "safety_score_above_80" in REWARD_TRIGGERS
    assert "week_no_high_risk" in REWARD_TRIGGERS
    assert "agreement_compliance_week" in REWARD_TRIGGERS

    assert REWARD_TRIGGERS["literacy_module_complete"]["type"] == "extra_time"
    assert REWARD_TRIGGERS["week_no_high_risk"]["type"] == "badge"

    assert 1 in BADGE_NAMES
    assert BADGE_NAMES[1] == "Safety Star"
