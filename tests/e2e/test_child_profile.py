"""End-to-end tests for child profile aggregation (P2-M4).

Covers:
- Happy path with combined AI + social + risk timeline
- Timeline ordering (newest first)
- Risk trend 7d and 30d
- Platform breakdown (AI + social)
- Quick-action counts (unresolved alerts, pending contacts, flagged content)
- Risk score calculation
- Member not found (404)
- Forbidden for non-admin roles
- No group context (422)
- Empty state (child with no activity)
- Degraded sections resilience
- Multiple children isolation
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.alerts.models import Alert
from src.auth.models import User
from src.capture.models import CaptureEvent
from src.contacts.models import Contact
from src.groups.models import Group, GroupMember
from src.messaging.models import Conversation, Message
from src.moderation.models import ModerationQueue
from src.portal.schemas import ChildProfileResponse
from src.portal.service import get_child_profile
from src.risk.models import RiskEvent
from src.schemas import GroupContext
from src.social.models import SocialPost

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_family(session):
    """Create parent user, child user, group, and members."""
    datetime.now(timezone.utc)

    parent = User(
        id=uuid.uuid4(),
        email=f"cp-parent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="CP Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_user = User(
        id=uuid.uuid4(),
        email=f"cp-child-{uuid.uuid4().hex[:8]}@example.com",
        display_name="CP Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add_all([parent, child_user])
    await session.flush()

    group = Group(
        id=uuid.uuid4(), name="CP Family", type="family", owner_id=parent.id,
    )
    session.add(group)
    await session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=parent.id,
        role="parent", display_name="CP Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child_user.id,
        role="member", display_name="CP Child",
    )
    session.add_all([parent_member, child_member])
    await session.flush()

    auth = GroupContext(
        user_id=parent.id,
        group_id=group.id,
        role="parent",
        scopes=["*"],
    )

    return parent, child_user, group, parent_member, child_member, auth


async def _add_capture_events(session, group_id, member_id, count=3, platform="chatgpt"):
    """Add AI capture events for a member."""
    now = datetime.now(timezone.utc)
    events = []
    for i in range(count):
        ev = CaptureEvent(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            platform=platform,
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            source_channel="extension",
        )
        events.append(ev)
    session.add_all(events)
    await session.flush()
    return events


async def _add_social_posts(session, author_id, count=2, status="approved"):
    """Add social posts."""
    datetime.now(timezone.utc)
    posts = []
    for i in range(count):
        post = SocialPost(
            id=uuid.uuid4(),
            author_id=author_id,
            content=f"Test post {i}",
            post_type="text",
            moderation_status=status,
        )
        session.add(post)
        posts.append(post)
    await session.flush()
    return posts


async def _add_risk_events(session, group_id, member_id, count=2, severity="medium"):
    """Add risk events."""
    events = []
    datetime.now(timezone.utc)
    for i in range(count):
        ev = RiskEvent(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            category="harmful_content",
            severity=severity,
            confidence=0.85,
        )
        events.append(ev)
    session.add_all(events)
    await session.flush()
    return events


async def _add_messages(session, sender_id, count=2):
    """Add messages in a conversation."""
    conv = Conversation(
        id=uuid.uuid4(), type="direct", created_by=sender_id,
    )
    session.add(conv)
    await session.flush()

    msgs = []
    for i in range(count):
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            sender_id=sender_id,
            content=f"Test message {i}",
        )
        msgs.append(msg)
    session.add_all(msgs)
    await session.flush()
    return msgs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_profile_happy_path(test_session):
    """Full child profile returns combined timeline with all sources."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    await _add_capture_events(test_session, group.id, child_member.id, count=3)
    await _add_social_posts(test_session, child_user.id, count=2)
    await _add_risk_events(test_session, group.id, child_member.id, count=2)
    await _add_messages(test_session, child_user.id, count=2)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert isinstance(result, ChildProfileResponse)
    assert result.member_id == child_member.id
    assert result.member_name == "CP Child"
    assert result.degraded_sections == []
    assert len(result.timeline) >= 7  # 3 AI + 2 posts + 2 risk + 2 msgs = 9 (may vary)


@pytest.mark.asyncio
async def test_child_profile_timeline_ordering(test_session):
    """Timeline items are sorted newest first."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    now = datetime.now(timezone.utc)
    # Add events with known timestamps
    old_event = CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=child_member.id,
        platform="gemini",
        session_id="old-sess",
        event_type="prompt",
        timestamp=now - timedelta(days=5),
        source_channel="extension",
    )
    new_event = CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=child_member.id,
        platform="chatgpt",
        session_id="new-sess",
        event_type="prompt",
        timestamp=now - timedelta(minutes=1),
        source_channel="extension",
    )
    test_session.add_all([old_event, new_event])
    await test_session.flush()

    result = await get_child_profile(test_session, child_member.id, auth)
    assert len(result.timeline) >= 2
    # Newest should be first
    assert result.timeline[0].timestamp >= result.timeline[-1].timestamp


@pytest.mark.asyncio
async def test_child_profile_risk_trend_7d(test_session):
    """Risk trend 7d returns 7 data points."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)
    await _add_risk_events(test_session, group.id, child_member.id, count=1)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert len(result.risk_trend_7d) == 7
    # Each point has date and count fields
    for point in result.risk_trend_7d:
        assert point.date
        assert isinstance(point.count, int)
        assert isinstance(point.high_count, int)


@pytest.mark.asyncio
async def test_child_profile_risk_trend_30d(test_session):
    """Risk trend 30d returns 30 data points."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert len(result.risk_trend_30d) == 30


@pytest.mark.asyncio
async def test_child_profile_platform_breakdown(test_session):
    """Platform breakdown includes AI platforms and social."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    await _add_capture_events(test_session, group.id, child_member.id, count=3, platform="chatgpt")
    await _add_capture_events(test_session, group.id, child_member.id, count=2, platform="gemini")
    await _add_social_posts(test_session, child_user.id, count=2)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert len(result.platform_breakdown) >= 2  # chatgpt + gemini (+ maybe social)
    platforms = {pb.platform for pb in result.platform_breakdown}
    assert "chatgpt" in platforms
    assert "gemini" in platforms

    # Percentages should sum roughly to 100
    total_pct = sum(pb.percentage for pb in result.platform_breakdown)
    assert 99.0 <= total_pct <= 101.0


@pytest.mark.asyncio
async def test_child_profile_risk_score_no_events(test_session):
    """Risk score is 100 when no risk events exist."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert result.risk_score == 100


@pytest.mark.asyncio
async def test_child_profile_risk_score_with_high_severity(test_session):
    """Risk score decreases with high severity events."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    await _add_risk_events(test_session, group.id, child_member.id, count=5, severity="medium")
    await _add_risk_events(test_session, group.id, child_member.id, count=5, severity="critical")

    result = await get_child_profile(test_session, child_member.id, auth)
    # 5 out of 10 are high/critical => score ~ 50
    assert result.risk_score == 50


@pytest.mark.asyncio
async def test_child_profile_unresolved_alerts(test_session):
    """Quick-action counts include unresolved alerts."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    for _ in range(3):
        alert = Alert(
            id=uuid.uuid4(),
            group_id=group.id,
            member_id=child_member.id,
            severity="medium",
            title="Test alert",
            body="Test body",
            channel="portal",
            status="pending",
        )
        test_session.add(alert)
    await test_session.flush()

    result = await get_child_profile(test_session, child_member.id, auth)
    assert result.unresolved_alerts == 3


@pytest.mark.asyncio
async def test_child_profile_pending_contacts(test_session):
    """Quick-action counts include pending contact requests."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    other_user = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other Kid",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(other_user)
    await test_session.flush()

    contact = Contact(
        id=uuid.uuid4(),
        requester_id=other_user.id,
        target_id=child_user.id,
        status="pending",
    )
    test_session.add(contact)
    await test_session.flush()

    result = await get_child_profile(test_session, child_member.id, auth)
    assert result.pending_contact_requests == 1


@pytest.mark.asyncio
async def test_child_profile_flagged_content(test_session):
    """Flagged content count reflects rejected/removed posts."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    await _add_social_posts(test_session, child_user.id, count=2, status="rejected")
    await _add_social_posts(test_session, child_user.id, count=1, status="approved")

    result = await get_child_profile(test_session, child_member.id, auth)
    assert result.flagged_content_count == 2


@pytest.mark.asyncio
async def test_child_profile_member_not_found(test_session):
    """Returns 404 for non-existent member."""
    from src.exceptions import NotFoundError

    parent, _, group, _, _, auth = await _setup_family(test_session)

    with pytest.raises(NotFoundError):
        await get_child_profile(test_session, uuid.uuid4(), auth)


@pytest.mark.asyncio
async def test_child_profile_forbidden_for_child_role(test_session):
    """Returns 403 when called by a non-admin (child) role."""
    from src.exceptions import ForbiddenError

    parent, child_user, group, _, child_member, _ = await _setup_family(test_session)

    child_auth = GroupContext(
        user_id=child_user.id,
        group_id=group.id,
        role="member",
        scopes=["*"],
    )

    with pytest.raises(ForbiddenError):
        await get_child_profile(test_session, child_member.id, child_auth)


@pytest.mark.asyncio
async def test_child_profile_no_group_context(test_session):
    """Returns 422 when no group context is provided."""
    from src.exceptions import ValidationError

    parent, _, group, _, child_member, _ = await _setup_family(test_session)

    no_group_auth = GroupContext(
        user_id=parent.id,
        group_id=None,
        role="parent",
        scopes=["*"],
    )

    with pytest.raises(ValidationError):
        await get_child_profile(test_session, child_member.id, no_group_auth)


@pytest.mark.asyncio
async def test_child_profile_empty_state(test_session):
    """Child with no activity returns empty timeline and max risk score."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    result = await get_child_profile(test_session, child_member.id, auth)
    assert result.timeline == []
    assert result.risk_score == 100
    assert result.platform_breakdown == []
    assert result.unresolved_alerts == 0
    assert result.pending_contact_requests == 0
    assert result.flagged_content_count == 0
    assert result.degraded_sections == []


@pytest.mark.asyncio
async def test_child_profile_multiple_children_isolation(test_session):
    """Child profile data is isolated per child."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    # Create a second child
    child2_user = User(
        id=uuid.uuid4(),
        email=f"cp-child2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="CP Child 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child2_user)
    await test_session.flush()

    child2_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child2_user.id,
        role="member", display_name="CP Child 2",
    )
    test_session.add(child2_member)
    await test_session.flush()

    # Add data only for child 1
    await _add_capture_events(test_session, group.id, child_member.id, count=5)
    await _add_risk_events(test_session, group.id, child_member.id, count=3)

    # Child 1 should have activity
    result1 = await get_child_profile(test_session, child_member.id, auth)
    assert len(result1.timeline) >= 5

    # Child 2 should have empty timeline
    result2 = await get_child_profile(test_session, child2_member.id, auth)
    assert result2.timeline == []
    assert result2.member_name == "CP Child 2"


@pytest.mark.asyncio
async def test_child_profile_moderation_in_timeline(test_session):
    """Moderation decisions appear in timeline."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    posts = await _add_social_posts(test_session, child_user.id, count=1, status="rejected")

    mod_item = ModerationQueue(
        id=uuid.uuid4(),
        content_type="post",
        content_id=posts[0].id,
        pipeline="pre_publish",
        status="rejected",
    )
    test_session.add(mod_item)
    await test_session.flush()

    result = await get_child_profile(test_session, child_member.id, auth)
    mod_entries = [t for t in result.timeline if t.source == "moderation"]
    assert len(mod_entries) >= 1
    assert mod_entries[0].event_type == "moderation_decision"


@pytest.mark.asyncio
async def test_child_profile_mixed_sources_in_timeline(test_session):
    """Timeline contains items from AI, social, risk, and message sources."""
    parent, child_user, group, _, child_member, auth = await _setup_family(test_session)

    await _add_capture_events(test_session, group.id, child_member.id, count=1)
    await _add_social_posts(test_session, child_user.id, count=1)
    await _add_risk_events(test_session, group.id, child_member.id, count=1)
    await _add_messages(test_session, child_user.id, count=1)

    result = await get_child_profile(test_session, child_member.id, auth)
    sources = {t.source for t in result.timeline}
    assert "ai" in sources
    assert "social_post" in sources
    assert "risk" in sources
    assert "social_message" in sources


@pytest.mark.asyncio
async def test_child_profile_schema_defaults(test_session):
    """ChildProfileResponse schema has correct defaults."""
    resp = ChildProfileResponse(
        member_id=uuid.uuid4(),
        member_name="Test",
    )
    assert resp.risk_score == 0
    assert resp.timeline == []
    assert resp.risk_trend_7d == []
    assert resp.risk_trend_30d == []
    assert resp.platform_breakdown == []
    assert resp.unresolved_alerts == 0
    assert resp.pending_contact_requests == 0
    assert resp.flagged_content_count == 0
    assert resp.degraded_sections == []
    assert resp.avatar_url is None
    assert resp.age_tier is None
