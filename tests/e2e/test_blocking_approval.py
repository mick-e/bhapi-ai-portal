"""E2E tests for blocking approval workflow and effectiveness."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.blocking.approval import (
    approve_unblock,
    deny_unblock,
    list_pending_approvals,
    request_unblock,
)
from src.blocking.approval_models import BlockApproval
from src.blocking.models import BlockRule
from src.blocking.service import get_block_effectiveness
from src.capture.models import CaptureEvent
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_request_unblock(test_session):
    """Submit an unblock request for an active block rule."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    approval = await request_unblock(
        test_session,
        group_id=group.id,
        block_rule_id=rule.id,
        member_id=member.id,
        reason="Homework is done",
    )
    assert approval.status == "pending"
    assert approval.reason == "Homework is done"
    assert approval.block_rule_id == rule.id


@pytest.mark.asyncio
async def test_request_unblock_nonexistent_rule(test_session):
    """Requesting unblock for a nonexistent rule should fail."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(NotFoundError):
        await request_unblock(
            test_session,
            group_id=group.id,
            block_rule_id=uuid4(),
            member_id=member.id,
            reason="Please unblock",
        )


@pytest.mark.asyncio
async def test_duplicate_pending_request(test_session):
    """Cannot create duplicate pending requests for the same rule."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    await request_unblock(
        test_session,
        group_id=group.id,
        block_rule_id=rule.id,
        member_id=member.id,
        reason="First request",
    )

    with pytest.raises(ValidationError):
        await request_unblock(
            test_session,
            group_id=group.id,
            block_rule_id=rule.id,
            member_id=member.id,
            reason="Duplicate request",
        )


@pytest.mark.asyncio
async def test_approve_unblock(test_session):
    """Approving an unblock request deactivates the block rule."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    approval = await request_unblock(
        test_session,
        group_id=group.id,
        block_rule_id=rule.id,
        member_id=member.id,
        reason="Finished chores",
    )

    result = await approve_unblock(
        test_session,
        approval_id=approval.id,
        decided_by=owner_id,
        decision_note="Good job",
    )
    assert result.status == "approved"
    assert result.decided_by == owner_id
    assert result.decision_note == "Good job"
    assert result.decided_at is not None

    # Block rule should now be inactive
    await test_session.refresh(rule)
    assert rule.active is False


@pytest.mark.asyncio
async def test_deny_unblock(test_session):
    """Denying an unblock request keeps the block rule active."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    approval = await request_unblock(
        test_session,
        group_id=group.id,
        block_rule_id=rule.id,
        member_id=member.id,
        reason="Want to use AI",
    )

    result = await deny_unblock(
        test_session,
        approval_id=approval.id,
        decided_by=owner_id,
        decision_note="Not yet",
    )
    assert result.status == "denied"
    assert result.decision_note == "Not yet"

    # Block rule should still be active
    await test_session.refresh(rule)
    assert rule.active is True


@pytest.mark.asyncio
async def test_cannot_approve_already_decided(test_session):
    """Cannot approve an already decided request."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    approval = await request_unblock(
        test_session,
        group_id=group.id,
        block_rule_id=rule.id,
        member_id=member.id,
        reason="Please",
    )

    await deny_unblock(test_session, approval_id=approval.id, decided_by=owner_id)

    with pytest.raises(ValidationError):
        await approve_unblock(test_session, approval_id=approval.id, decided_by=owner_id)


@pytest.mark.asyncio
async def test_approve_nonexistent_approval(test_session):
    """Approving a nonexistent approval should fail."""
    with pytest.raises(NotFoundError):
        await approve_unblock(test_session, approval_id=uuid4(), decided_by=uuid4())


@pytest.mark.asyncio
async def test_list_pending_approvals(test_session):
    """List only pending approvals for a group."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule1 = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    rule2 = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member.id,
        active=True, created_by=owner_id,
    )
    test_session.add_all([rule1, rule2])
    await test_session.flush()

    approval1 = await request_unblock(
        test_session, group_id=group.id, block_rule_id=rule1.id,
        member_id=member.id, reason="Request 1",
    )
    approval2 = await request_unblock(
        test_session, group_id=group.id, block_rule_id=rule2.id,
        member_id=member.id, reason="Request 2",
    )

    # Deny one
    await deny_unblock(test_session, approval_id=approval1.id, decided_by=owner_id)

    pending = await list_pending_approvals(test_session, group_id=group.id)
    assert len(pending) == 1
    assert pending[0].id == approval2.id


@pytest.mark.asyncio
async def test_effectiveness_no_data(test_session):
    """Effectiveness returns zeros when no data exists."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    result = await get_block_effectiveness(test_session, group_id=group.id)
    assert result["total_rules"] == 0
    assert result["blocked_count"] == 0
    assert result["total_events"] == 0
    assert result["block_rate_pct"] == 0.0


@pytest.mark.asyncio
async def test_effectiveness_with_data(test_session):
    """Effectiveness returns correct metrics with rules and events."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member1 = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child 1",
    )
    member2 = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child 2",
    )
    test_session.add_all([member1, member2])
    await test_session.flush()

    # Create active block rules for member1
    rule = BlockRule(
        id=uuid4(), group_id=group.id, member_id=member1.id,
        active=True, created_by=owner_id,
    )
    test_session.add(rule)

    # Create capture events
    now = datetime.now(timezone.utc)
    for i in range(3):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member1.id,
            platform="chatgpt", session_id=f"sess-{i}",
            event_type="prompt", timestamp=now,
        )
        test_session.add(event)
    await test_session.flush()

    result = await get_block_effectiveness(test_session, group_id=group.id)
    assert result["total_rules"] == 1
    assert result["blocked_count"] == 1
    assert result["total_events"] == 3
    assert result["block_rate_pct"] > 0
