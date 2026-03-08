"""E2E tests for EU AI Act compliance features."""

import pytest
from uuid import uuid4

from src.compliance.eu_ai_act import (
    get_algorithmic_transparency,
    request_human_review,
    submit_appeal,
    list_appeals,
    resolve_appeal,
)
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember
from src.risk.models import RiskEvent
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_algorithmic_transparency(test_session):
    """Transparency endpoint should return classification details."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")

    result = await get_algorithmic_transparency(test_session, group.id)
    assert result["system_name"] == "Bhapi AI Safety Monitor"
    assert result["right_to_explanation"] is True
    assert result["right_to_human_review"] is True
    assert result["right_to_appeal"] is True
    assert isinstance(result["categories"], list)


@pytest.mark.asyncio
async def test_human_review_flow(test_session):
    """Full human review request flow."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    member = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="parent", display_name="P")
    test_session.add(member)
    await test_session.flush()

    risk = RiskEvent(
        id=uuid4(), group_id=group.id, member_id=member.id,
        category="test", severity="high", confidence=0.9,
        details={}, acknowledged=False,
    )
    test_session.add(risk)
    await test_session.flush()

    review = await request_human_review(test_session, risk.id, group.owner_id, group.id)
    assert review.status == "pending"
    assert review.risk_event_id == risk.id


@pytest.mark.asyncio
async def test_duplicate_human_review_rejected(test_session):
    """Duplicate human review request should be rejected."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    member = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="parent", display_name="P")
    test_session.add(member)
    await test_session.flush()

    risk = RiskEvent(
        id=uuid4(), group_id=group.id, member_id=member.id,
        category="test", severity="high", confidence=0.9,
        details={}, acknowledged=False,
    )
    test_session.add(risk)
    await test_session.flush()

    await request_human_review(test_session, risk.id, group.owner_id, group.id)

    with pytest.raises(ValidationError, match="already pending"):
        await request_human_review(test_session, risk.id, group.owner_id, group.id)


@pytest.mark.asyncio
async def test_appeal_submission_and_resolution(test_session):
    """Full appeal flow: submit → resolve (overturn)."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    member = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="parent", display_name="P")
    test_session.add(member)
    await test_session.flush()

    risk = RiskEvent(
        id=uuid4(), group_id=group.id, member_id=member.id,
        category="test", severity="medium", confidence=0.7,
        details={}, acknowledged=False,
    )
    test_session.add(risk)
    await test_session.flush()

    # Submit appeal (use owner_id since member.user_id is None for monitored members)
    appeal = await submit_appeal(
        test_session, risk.id, owner_id, group.id,
        "This was a false positive — the content was educational."
    )
    assert appeal.status == "pending"

    # List appeals
    appeals, total = await list_appeals(test_session, group.id)
    assert total == 1

    # Resolve appeal (overturn)
    resolved = await resolve_appeal(
        test_session, appeal.id, group.owner_id,
        "overturned", "Confirmed as educational content."
    )
    assert resolved.status == "resolved"
    assert resolved.resolution == "overturned"

    # Risk event should be acknowledged after overturn
    from sqlalchemy import select
    result = await test_session.execute(select(RiskEvent).where(RiskEvent.id == risk.id))
    updated_risk = result.scalar_one()
    assert updated_risk.acknowledged is True


@pytest.mark.asyncio
async def test_appeal_nonexistent_risk_event(test_session):
    """Appeal for nonexistent risk event should fail."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")

    with pytest.raises(NotFoundError):
        await submit_appeal(test_session, uuid4(), uuid4(), group.id, "reason")
