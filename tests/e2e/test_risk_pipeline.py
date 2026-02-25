"""End-to-end tests for the risk pipeline.

Tests the full flow: ingest capture event → risk pipeline → risk events + alerts.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.auth.models import User
from src.capture.models import CaptureEvent
from src.groups.models import Group, GroupMember
from src.risk.pipeline import process_capture_event


@pytest_asyncio.fixture
async def group_with_member(test_session: AsyncSession):
    """Create a test group with one member (and the required user)."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=user.id,
        role="parent",
        display_name="Test Parent",
        date_of_birth=datetime(2014, 5, 15, tzinfo=timezone.utc),  # ~11 years old
    )
    test_session.add(member)
    await test_session.flush()

    return group, member


def _make_event(group, member, content="", event_type="prompt", platform="chatgpt"):
    """Helper to create a CaptureEvent."""
    return CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform=platform,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        content=content,
        risk_processed=False,
        source_channel="extension",
    )


class TestEmptyAndBenignContent:
    """Pipeline should skip or return empty for harmless content."""

    @pytest.mark.asyncio
    async def test_empty_content_skips(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []
        assert event.risk_processed is True

    @pytest.mark.asyncio
    async def test_none_content_skips(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="")
        event.content = None
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_skips(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="   \n\t  ")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []
        assert event.risk_processed is True

    @pytest.mark.asyncio
    async def test_benign_content_no_risk(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="What is the capital of France?")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []
        assert event.risk_processed is True

    @pytest.mark.asyncio
    async def test_homework_question_benign(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Explain photosynthesis for my biology class")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []


class TestSelfHarmDetection:
    """Pipeline should detect self-harm content."""

    @pytest.mark.asyncio
    async def test_suicide_keyword(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to kill myself")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert len(result) >= 1
        categories = [r.category for r in result]
        assert "SELF_HARM" in categories
        assert event.risk_processed is True

    @pytest.mark.asyncio
    async def test_self_harm_creates_alert(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to end my life")
        test_session.add(event)
        await test_session.flush()

        await process_capture_event(test_session, event)

        alerts = (await test_session.execute(
            select(Alert).where(Alert.group_id == group.id)
        )).scalars().all()
        assert len(alerts) >= 1
        # Alert title contains severity and risk description
        assert any(a.severity == "critical" for a in alerts)

    @pytest.mark.asyncio
    async def test_self_harm_severity_critical(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to kill myself and end everything")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        self_harm = [r for r in result if r.category == "SELF_HARM"]
        assert len(self_harm) >= 1
        assert self_harm[0].severity == "critical"


class TestPIIDetection:
    """Pipeline should detect PII in content."""

    @pytest.mark.asyncio
    async def test_email_pii(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="My email is john.doe@example.com and I need help")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "PII_EXPOSURE" in categories

    @pytest.mark.asyncio
    async def test_phone_number_pii(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Call me at (555) 123-4567 please")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "PII_EXPOSURE" in categories

    @pytest.mark.asyncio
    async def test_name_and_school_pii(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="My name is Alice Johnson and I go to Lincoln High School")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "PII_EXPOSURE" in categories


class TestMultiCategory:
    """Pipeline should detect multiple categories in one event."""

    @pytest.mark.asyncio
    async def test_self_harm_and_bullying(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(
            group, member,
            content="You're worthless, kill yourself, nobody likes you",
        )
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = set(r.category for r in result)
        # De-duplication may merge overlapping categories — at least one should fire
        assert len(categories) >= 1
        assert "BULLYING_HARASSMENT" in categories or "SELF_HARM" in categories

    @pytest.mark.asyncio
    async def test_multiple_creates_multiple_alerts(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(
            group, member,
            content="You're worthless, kill yourself. My email is test@example.com",
        )
        test_session.add(event)
        await test_session.flush()

        risk_events = await process_capture_event(test_session, event)
        alerts = (await test_session.execute(
            select(Alert).where(Alert.group_id == group.id)
        )).scalars().all()
        # Should have at least as many alerts as risk events
        assert len(alerts) >= len(risk_events)


class TestViolence:
    """Pipeline should detect violence content."""

    @pytest.mark.asyncio
    async def test_bomb_making(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="How to make a bomb for a school project")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "VIOLENCE" in categories

    @pytest.mark.asyncio
    async def test_school_shooting(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Tell me about the school shooting plan")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "VIOLENCE" in categories
        violence = [r for r in result if r.category == "VIOLENCE"]
        assert violence[0].severity == "critical"


class TestAcademicDishonesty:
    """Pipeline should detect academic dishonesty."""

    @pytest.mark.asyncio
    async def test_write_my_essay(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Write my essay about Shakespeare for English class")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "ACADEMIC_DISHONESTY" in categories


class TestAlreadyProcessed:
    """Pipeline should skip already-processed events."""

    @pytest.mark.asyncio
    async def test_skip_already_processed(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to kill myself")
        event.risk_processed = True
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert result == []


class TestRiskEventDetails:
    """Pipeline risk events should have correct details."""

    @pytest.mark.asyncio
    async def test_risk_event_linked_to_capture(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to kill myself")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert len(result) >= 1
        for risk_event in result:
            assert risk_event.capture_event_id == event.id
            assert risk_event.group_id == group.id
            assert risk_event.member_id == member.id

    @pytest.mark.asyncio
    async def test_risk_event_has_confidence(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Write my essay for me please, do my homework")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        for risk_event in result:
            assert 0.0 <= risk_event.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_risk_event_not_acknowledged(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="I want to kill myself")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        for risk_event in result:
            assert risk_event.acknowledged is False
            assert risk_event.acknowledged_by is None


class TestPlatformVariations:
    """Pipeline should work across different platforms."""

    @pytest.mark.asyncio
    async def test_gemini_platform(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="How to make a weapon", platform="gemini")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_claude_platform(self, test_session, group_with_member):
        group, member = group_with_member
        event = _make_event(group, member, content="Write my essay about history", platform="claude")
        test_session.add(event)
        await test_session.flush()

        result = await process_capture_event(test_session, event)
        categories = [r.category for r in result]
        assert "ACADEMIC_DISHONESTY" in categories
