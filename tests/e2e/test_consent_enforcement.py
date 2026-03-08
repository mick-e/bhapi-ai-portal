"""E2E tests for consent enforcement before capture (Phase 1I)."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.capture.schemas import EventPayload
from src.capture.service import ingest_event
from src.compliance.models import ConsentRecord
from src.exceptions import ForbiddenError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_capture_blocked_without_consent(test_session):
    """Capture should be blocked for minor without consent."""
    group, owner_id = await make_test_group(test_session, name="Test Family", group_type="family")

    # Minor member (age 10)
    minor_id = uuid4()
    minor = GroupMember(
        id=minor_id, group_id=group.id,
        user_id=None, role="member",
        display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(minor)
    await test_session.flush()

    payload = EventPayload(
        group_id=group.id,
        member_id=minor_id,
        platform="chatgpt",
        session_id="test-session",
        event_type="prompt",
        timestamp=datetime.now(timezone.utc),
        content="Hello world",
    )

    with pytest.raises(ForbiddenError, match="consent required"):
        await ingest_event(test_session, payload)


@pytest.mark.asyncio
async def test_capture_allowed_with_consent(test_session):
    """Capture should proceed when consent is recorded."""
    group, owner_id = await make_test_group(test_session, name="Test Family", group_type="family")

    minor_id = uuid4()
    minor = GroupMember(
        id=minor_id, group_id=group.id,
        user_id=None, role="member",
        display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(minor)
    await test_session.flush()

    # Record consent
    consent = ConsentRecord(
        id=uuid4(), group_id=group.id,
        member_id=minor_id,
        consent_type="monitoring",
        parent_user_id=owner_id,
    )
    test_session.add(consent)
    await test_session.flush()

    payload = EventPayload(
        group_id=group.id,
        member_id=minor_id,
        platform="chatgpt",
        session_id="test-session",
        event_type="prompt",
        timestamp=datetime.now(timezone.utc),
        content="Hello world",
    )

    event = await ingest_event(test_session, payload)
    assert event is not None
    assert event.platform == "chatgpt"


@pytest.mark.asyncio
async def test_capture_allowed_for_adult(test_session):
    """Capture should proceed for adults without consent."""
    group, owner_id = await make_test_group(test_session, name="Test Family", group_type="family")

    # Adult member (no DOB = no consent needed)
    adult_id = uuid4()
    adult = GroupMember(
        id=adult_id, group_id=group.id,
        user_id=owner_id, role="parent",
        display_name="Parent",
    )
    test_session.add(adult)
    await test_session.flush()

    payload = EventPayload(
        group_id=group.id,
        member_id=adult_id,
        platform="chatgpt",
        session_id="test-session",
        event_type="prompt",
        timestamp=datetime.now(timezone.utc),
    )

    event = await ingest_event(test_session, payload)
    assert event is not None
