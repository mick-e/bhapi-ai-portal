"""Security tests for COPPA verifiable consent bypass prevention."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.capture.schemas import EventPayload
from src.capture.service import ingest_event
from src.compliance.models import ConsentRecord
from src.exceptions import ForbiddenError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_under13_requires_consent(test_session):
    """Children under 13 (US COPPA) must have consent before capture."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    # Child aged 10
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    payload = EventPayload(
        group_id=group.id, member_id=child.id,
        platform="chatgpt", session_id="s1",
        event_type="prompt",
        timestamp=datetime.now(timezone.utc),
        content="test",
    )

    with pytest.raises(ForbiddenError, match="consent required"):
        await ingest_event(test_session, payload)


@pytest.mark.asyncio
async def test_withdrawn_consent_blocks_capture(test_session):
    """Withdrawn consent should block capture for minors."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    # Consent that was withdrawn
    consent = ConsentRecord(
        id=uuid4(), group_id=group.id, member_id=child.id,
        consent_type="monitoring", parent_user_id=group.owner_id,
        withdrawn_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    test_session.add(consent)
    await test_session.flush()

    payload = EventPayload(
        group_id=group.id, member_id=child.id,
        platform="chatgpt", session_id="s1",
        event_type="prompt",
        timestamp=datetime.now(timezone.utc),
        content="test",
    )

    with pytest.raises(ForbiddenError, match="consent required"):
        await ingest_event(test_session, payload)
