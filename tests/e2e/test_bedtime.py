"""E2E tests for bedtime mode — rule creation, retrieval, and removal."""

import pytest
from uuid import uuid4

from src.blocking.service import (
    set_bedtime_mode,
    get_bedtime_mode,
    delete_bedtime_mode,
)
from src.blocking.models import AutoBlockRule, BlockRule
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember
from sqlalchemy import select
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_set_bedtime_mode(test_session):
    """Create bedtime mode for a member."""
    group, owner_id = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = await set_bedtime_mode(
        test_session,
        group_id=group.id,
        member_id=member.id,
        start_hour=21,
        end_hour=7,
    )
    assert rule.name == "Bedtime mode"
    assert rule.trigger_type == "time_of_day"
    assert rule.trigger_config["start_hour"] == 21
    assert rule.trigger_config["end_hour"] == 7
    assert rule.enabled is True
    assert rule.schedule_start == "21:00"
    assert rule.schedule_end == "07:00"


@pytest.mark.asyncio
async def test_get_bedtime_mode(test_session):
    """Retrieve bedtime config for a member."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # No bedtime set yet
    result = await get_bedtime_mode(test_session, group.id, member.id)
    assert result is None

    # Set bedtime
    await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=20, end_hour=6,
    )

    result = await get_bedtime_mode(test_session, group.id, member.id)
    assert result is not None
    assert result.trigger_config["start_hour"] == 20


@pytest.mark.asyncio
async def test_update_bedtime_mode(test_session):
    """Updating bedtime mode modifies the existing rule."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule1 = await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=21, end_hour=7,
    )
    rule2 = await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=22, end_hour=8,
    )

    # Same rule ID, updated config
    assert rule1.id == rule2.id
    assert rule2.trigger_config["start_hour"] == 22
    assert rule2.schedule_start == "22:00"


@pytest.mark.asyncio
async def test_delete_bedtime_mode(test_session):
    """Deleting bedtime mode removes the rule."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=21, end_hour=7,
    )

    await delete_bedtime_mode(test_session, group.id, member.id)

    result = await get_bedtime_mode(test_session, group.id, member.id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_bedtime_mode_not_found(test_session):
    """Deleting non-existent bedtime mode raises NotFoundError."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(NotFoundError):
        await delete_bedtime_mode(test_session, group.id, member.id)


@pytest.mark.asyncio
async def test_delete_bedtime_mode_deactivates_blocks(test_session):
    """Deleting bedtime mode deactivates any active blocks it created."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=21, end_hour=7,
    )

    # Simulate block created by bedtime rule
    block = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        reason="Auto-blocked: scheduled block (21:00-07:00)",
        active=True,
        created_by=group.owner_id,
        auto_rule_id=rule.id,
    )
    test_session.add(block)
    await test_session.flush()

    await delete_bedtime_mode(test_session, group.id, member.id)

    # Block should be deactivated
    updated_block = await test_session.execute(
        select(BlockRule).where(BlockRule.id == block.id)
    )
    b = updated_block.scalar_one()
    assert b.active is False


@pytest.mark.asyncio
async def test_set_bedtime_mode_invalid_hours(test_session):
    """Invalid hours should be rejected."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(ValidationError):
        await set_bedtime_mode(
            test_session, group.id, member.id,
            start_hour=25, end_hour=7,
        )


@pytest.mark.asyncio
async def test_bedtime_mode_with_timezone(test_session):
    """Bedtime mode stores timezone info."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = await set_bedtime_mode(
        test_session, group.id, member.id,
        start_hour=21, end_hour=7, tz="America/New_York",
    )
    assert rule.trigger_config["timezone"] == "America/New_York"
