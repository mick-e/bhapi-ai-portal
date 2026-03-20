"""Unit tests for content excerpt TTL cleanup job."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.groups.models import GroupMember
from src.risk.models import ContentExcerpt, RiskEvent
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_cleanup_deletes_expired(test_session):
    """Expired excerpts should be deleted by cleanup job."""
    from src.risk.cleanup import cleanup_expired_excerpts

    group, owner_id = await make_test_group(test_session, name="T", group_type="family")
    member = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="parent", display_name="P")
    test_session.add(member)
    await test_session.flush()

    risk = RiskEvent(
        id=uuid4(), group_id=group.id, member_id=member.id,
        category="test", severity="low", confidence=0.5,
        details={}, acknowledged=False,
    )
    test_session.add(risk)
    await test_session.flush()

    # Expired excerpt
    expired = ContentExcerpt(
        id=uuid4(), risk_event_id=risk.id,
        encrypted_content="fernet:old",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # Still valid excerpt
    valid = ContentExcerpt(
        id=uuid4(), risk_event_id=risk.id,
        encrypted_content="fernet:new",
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    test_session.add_all([expired, valid])
    await test_session.flush()

    deleted = await cleanup_expired_excerpts(test_session)
    assert deleted == 1


@pytest.mark.asyncio
async def test_cleanup_no_expired(test_session):
    """Cleanup should return 0 when nothing is expired."""
    from src.risk.cleanup import cleanup_expired_excerpts

    deleted = await cleanup_expired_excerpts(test_session)
    assert deleted == 0
