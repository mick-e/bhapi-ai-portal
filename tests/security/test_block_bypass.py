"""Security tests for block check bypass prevention."""

import pytest
from uuid import uuid4

from src.blocking.models import BlockRule
from src.blocking.service import check_block_status, create_block_rule
from src.blocking.schemas import BlockRuleCreate
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_block_status_requires_correct_group(test_session):
    """Block check should only return rules for the correct group."""
    group_a, owner_a_id = await make_test_group(test_session, name="Group A", group_type="family")
    group_b, owner_b_id = await make_test_group(test_session, name="Group B", group_type="family")

    member = GroupMember(
        id=uuid4(), group_id=group_a.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Block in group A
    rule = BlockRule(
        id=uuid4(), group_id=group_a.id, member_id=member.id,
        active=True, created_by=group_a.owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    # Check in group A — should be blocked
    status_a = await check_block_status(test_session, group_a.id, member.id)
    assert status_a["blocked"] is True

    # Check in group B — should NOT be blocked
    status_b = await check_block_status(test_session, group_b.id, member.id)
    assert status_b["blocked"] is False


@pytest.mark.asyncio
async def test_expired_block_not_active(test_session):
    """Expired block rules should not be returned as active."""
    from datetime import datetime, timedelta, timezone

    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Add an expired block
    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=group.owner_id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    test_session.add(rule)
    await test_session.flush()

    status = await check_block_status(test_session, group.id, member.id)
    assert status["blocked"] is False
