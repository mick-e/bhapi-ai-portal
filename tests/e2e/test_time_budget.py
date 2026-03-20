"""E2E tests for time budget CRUD and enforcement."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from src.blocking.models import BlockRule
from src.blocking.time_budget import (
    check_time_budget,
    enforce_time_budgets,
    get_usage_history,
    record_session_time,
    set_time_budget,
)
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_full_time_budget_lifecycle(test_session):
    """Full lifecycle: create budget, record time, check status."""
    group, owner_id = await make_test_group(test_session, name="Budget Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # 1. Create budget
    budget = await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=60, weekend_minutes=120,
    )
    assert budget.id is not None

    # 2. Check status — no usage yet
    status = await check_time_budget(test_session, group.id, member.id)
    assert status["enabled"] is True
    assert status["minutes_used"] == 0
    assert status["exceeded"] is False

    # 3. Record some time
    await record_session_time(test_session, group.id, member.id, 20)
    status = await check_time_budget(test_session, group.id, member.id)
    assert status["minutes_used"] == 20

    # 4. Record more time
    await record_session_time(test_session, group.id, member.id, 30)
    status = await check_time_budget(test_session, group.id, member.id)
    assert status["minutes_used"] == 50

    # 5. Get history
    history = await get_usage_history(test_session, group.id, member.id)
    assert len(history) == 1
    assert history[0]["minutes_used"] == 50


@pytest.mark.asyncio
async def test_time_budget_enforcement_blocks_exceeded(test_session):
    """Enforcement creates a block rule when budget is exceeded."""
    group, owner_id = await make_test_group(test_session, name="Budget Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Set budget and exceed it
    await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=30, weekend_minutes=30,
    )
    await record_session_time(test_session, group.id, member.id, 35)

    # Run enforcement
    result = await enforce_time_budgets(test_session)
    assert result["blocked"] >= 1

    # Verify block rule exists
    blocks_result = await test_session.execute(
        select(BlockRule).where(
            BlockRule.group_id == group.id,
            BlockRule.member_id == member.id,
            BlockRule.reason == "Time budget exceeded",
            BlockRule.active.is_(True),
        )
    )
    block = blocks_result.scalar_one_or_none()
    assert block is not None


@pytest.mark.asyncio
async def test_time_budget_enforcement_no_double_block(test_session):
    """Enforcement does not create duplicate block rules."""
    group, owner_id = await make_test_group(test_session, name="Budget Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=30, weekend_minutes=30,
    )
    await record_session_time(test_session, group.id, member.id, 35)

    # Run enforcement twice
    await enforce_time_budgets(test_session)
    result = await enforce_time_budgets(test_session)
    assert result["blocked"] == 0  # already blocked


@pytest.mark.asyncio
async def test_time_budget_enforcement_unblocks_under_budget(test_session):
    """Enforcement removes block when member is under budget."""
    group, owner_id = await make_test_group(test_session, name="Budget Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Create budget and a fake time-budget block
    await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=120, weekend_minutes=120,
    )
    block = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        reason="Time budget exceeded",
        active=True,
        created_by=owner_id,
    )
    test_session.add(block)
    await test_session.flush()

    # No usage recorded, so under budget — enforcement should unblock
    result = await enforce_time_budgets(test_session)
    assert result["unblocked"] >= 1


@pytest.mark.asyncio
async def test_time_budget_update(test_session):
    """Update an existing time budget."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    budget1 = await set_time_budget(
        test_session, group.id, member.id, weekday_minutes=60
    )
    budget2 = await set_time_budget(
        test_session, group.id, member.id, weekday_minutes=90
    )

    # Same record updated
    assert budget1.id == budget2.id
    assert budget2.weekday_minutes == 90


@pytest.mark.asyncio
async def test_time_budget_disabled_budget_not_enforced(test_session):
    """Disabled budgets are not enforced."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_time_budget(
        test_session, group.id, member.id,
        weekday_minutes=30, weekend_minutes=30, enabled=False,
    )
    await record_session_time(test_session, group.id, member.id, 100)

    result = await enforce_time_budgets(test_session)
    assert result["blocked"] == 0
