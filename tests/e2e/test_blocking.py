"""E2E tests for AI session blocking."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.blocking.models import BlockRule
from src.blocking.schemas import BlockRuleCreate
from src.blocking.service import (
    check_block_status,
    create_block_rule,
    get_active_blocks,
    revoke_block,
)
from src.exceptions import NotFoundError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_create_block_rule(test_session):
    """Create a block rule for a member."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = await create_block_rule(
        test_session,
        BlockRuleCreate(
            group_id=group.id,
            member_id=member.id,
            platforms=["chatgpt", "gemini"],
            reason="Exceeded usage limits",
        ),
        user_id=group.owner_id,
    )
    assert rule.active is True
    assert rule.platforms == ["chatgpt", "gemini"]


@pytest.mark.asyncio
async def test_check_block_status(test_session):
    """Block status should reflect active rules."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Not blocked initially
    status = await check_block_status(test_session, group.id, member.id)
    assert status["blocked"] is False

    # Add block rule
    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=group.owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    # Now blocked
    status = await check_block_status(test_session, group.id, member.id)
    assert status["blocked"] is True


@pytest.mark.asyncio
async def test_revoke_block(test_session):
    """Revoking a block should deactivate it."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=group.owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    revoked = await revoke_block(test_session, rule.id)
    assert revoked.active is False

    status = await check_block_status(test_session, group.id, member.id)
    assert status["blocked"] is False


@pytest.mark.asyncio
async def test_revoke_nonexistent_block(test_session):
    """Revoking a nonexistent block should fail."""
    with pytest.raises(NotFoundError):
        await revoke_block(test_session, uuid4())


@pytest.mark.asyncio
async def test_expired_block_ignored(test_session):
    """Expired block rules should not count as active."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=group.owner_id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    test_session.add(rule)
    await test_session.flush()

    blocks = await get_active_blocks(test_session, group.id, member.id)
    assert len(blocks) == 0
