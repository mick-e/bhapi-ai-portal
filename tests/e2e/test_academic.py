"""E2E tests for Academic Integrity analytics endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.analytics.academic import generate_academic_report
from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_academic_report_empty(test_session):
    """Academic report for a member with no events returns zeros."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    today = datetime.now(timezone.utc).date()
    report = await generate_academic_report(
        test_session,
        group.id,
        member.id,
        today - timedelta(days=7),
        today,
    )
    assert report.total_ai_sessions == 0
    assert report.learning_count == 0
    assert report.doing_count == 0
    assert report.unclassified_count == 0
    assert report.learning_ratio == 0.0
    assert "No AI sessions" in report.recommendation


@pytest.mark.asyncio
async def test_academic_report_with_events(test_session):
    """Academic report correctly classifies events with content."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Student",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Learning event
    learn_event = CaptureEvent(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        session_id="s1",
        event_type="prompt",
        content="Explain how photosynthesis works",
        timestamp=now - timedelta(hours=2),
        risk_processed=False,
        source_channel="extension",
    )
    test_session.add(learn_event)

    # Doing event
    doing_event = CaptureEvent(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        session_id="s2",
        event_type="prompt",
        content="Write my essay about climate change",
        timestamp=now - timedelta(hours=1),
        risk_processed=False,
        source_channel="extension",
    )
    test_session.add(doing_event)

    # Unclassified event
    other_event = CaptureEvent(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        session_id="s3",
        event_type="prompt",
        content="Tell me a joke",
        timestamp=now,
        risk_processed=False,
        source_channel="extension",
    )
    test_session.add(other_event)
    await test_session.flush()

    today = now.date()
    report = await generate_academic_report(
        test_session,
        group.id,
        member.id,
        today - timedelta(days=1),
        today,
    )

    assert report.total_ai_sessions == 3
    assert report.learning_count == 1
    assert report.doing_count == 1
    assert report.unclassified_count == 1
    assert report.learning_ratio == 0.5  # 1 learning out of 2 classified
    assert len(report.daily_breakdown) >= 1


@pytest.mark.asyncio
async def test_academic_endpoint_requires_auth(client):
    """GET /api/v1/analytics/academic requires authentication."""
    resp = await client.get(
        "/api/v1/analytics/academic",
        params={"member_id": str(uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_intent_endpoint_requires_auth(client):
    """GET /api/v1/analytics/academic/intent requires authentication."""
    resp = await client.get(
        "/api/v1/analytics/academic/intent",
        params={"text": "explain photosynthesis"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_academic_report_study_hours(test_session):
    """Study hour sessions are correctly counted."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Wednesday at 16:00 (within weekday study hours)
    study_ts = datetime(2026, 3, 11, 16, 0, tzinfo=timezone.utc)
    # Wednesday at 08:00 (outside weekday study hours)
    non_study_ts = datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc)

    for i, ts in enumerate([study_ts, non_study_ts]):
        event = CaptureEvent(
            id=uuid4(),
            group_id=group.id,
            member_id=member.id,
            platform="chatgpt",
            session_id=f"s{i}",
            event_type="prompt",
            content="Tell me something",
            timestamp=ts,
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    report = await generate_academic_report(
        test_session,
        group.id,
        member.id,
        study_ts.date(),
        study_ts.date(),
    )
    assert report.total_ai_sessions == 2
    assert report.study_hour_sessions == 1
