"""Unit tests for emotional dependency scoring module.

Tests score calculation edge cases, threshold triggers, and trend detection.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.capture.models import CaptureEvent
from src.groups.models import Group, GroupMember
from src.risk.emotional_dependency import (
    ALERT_THRESHOLD,
    COMPANION_PLATFORMS,
    CRITICAL_THRESHOLD,
    DependencyScore,
    _score_frequency,
    _score_session_duration,
    _score_time_pattern,
    _score_attachment_language,
    _build_recommendation,
    calculate_dependency_score,
    check_dependency_alerts,
)
from src.risk.models import RiskEvent


@pytest_asyncio.fixture
async def group_with_member(test_session: AsyncSession):
    """Create a test group with one child member."""
    user = User(
        id=uuid.uuid4(),
        email=f"parent-{uuid.uuid4().hex[:8]}@example.com",
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
        role="member",
        display_name="Test Child",
        date_of_birth=datetime(2014, 5, 15, tzinfo=timezone.utc),
    )
    test_session.add(member)
    await test_session.flush()

    return group, member


def _make_capture_event(
    group,
    member,
    platform="characterai",
    session_id=None,
    timestamp=None,
    content="Hello there",
):
    """Create a CaptureEvent for testing."""
    return CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform=platform,
        session_id=session_id or f"sess-{uuid.uuid4().hex[:8]}",
        event_type="prompt",
        timestamp=timestamp or datetime.now(timezone.utc),
        content=content,
        risk_processed=False,
        source_channel="extension",
    )


class TestScoreFunctions:
    """Test individual sub-score functions."""

    def test_session_duration_score_low(self):
        assert _score_session_duration(5) == 0
        assert _score_session_duration(14) == 0

    def test_session_duration_score_medium(self):
        assert _score_session_duration(15) == 8
        assert _score_session_duration(29) == 8

    def test_session_duration_score_high(self):
        assert _score_session_duration(30) == 15
        assert _score_session_duration(44) == 15

    def test_session_duration_score_very_high(self):
        assert _score_session_duration(45) == 20
        assert _score_session_duration(59) == 20

    def test_session_duration_score_max(self):
        assert _score_session_duration(60) == 25
        assert _score_session_duration(120) == 25

    def test_frequency_score_low(self):
        assert _score_frequency(0) == 0
        assert _score_frequency(1) == 0

    def test_frequency_score_medium(self):
        assert _score_frequency(2) == 8
        assert _score_frequency(3) == 8

    def test_frequency_score_high(self):
        assert _score_frequency(4) == 15
        assert _score_frequency(5) == 15

    def test_frequency_score_very_high(self):
        assert _score_frequency(6) == 20
        assert _score_frequency(8) == 20

    def test_frequency_score_max(self):
        assert _score_frequency(9) == 25
        assert _score_frequency(20) == 25

    def test_time_pattern_score_low(self):
        assert _score_time_pattern(0) == 0
        assert _score_time_pattern(9) == 0

    def test_time_pattern_score_medium(self):
        assert _score_time_pattern(10) == 8
        assert _score_time_pattern(24) == 8

    def test_time_pattern_score_high(self):
        assert _score_time_pattern(25) == 15
        assert _score_time_pattern(49) == 15

    def test_time_pattern_score_very_high(self):
        assert _score_time_pattern(50) == 20
        assert _score_time_pattern(74) == 20

    def test_time_pattern_score_max(self):
        assert _score_time_pattern(75) == 25
        assert _score_time_pattern(100) == 25

    def test_attachment_language_score_zero(self):
        assert _score_attachment_language(0.0) == 0

    def test_attachment_language_score_moderate(self):
        assert _score_attachment_language(0.15) == 15

    def test_attachment_language_score_capped(self):
        assert _score_attachment_language(0.50) == 25
        assert _score_attachment_language(1.0) == 25


class TestRecommendations:
    """Test recommendation text generation."""

    def test_healthy_recommendation(self):
        rec = _build_recommendation(10)
        assert "healthy" in rec.lower() or "no action" in rec.lower()

    def test_minor_recommendation(self):
        rec = _build_recommendation(30)
        assert "casual" in rec.lower() or "conversation" in rec.lower()

    def test_moderate_recommendation(self):
        rec = _build_recommendation(50)
        assert "moderate" in rec.lower() or "boundaries" in rec.lower()

    def test_significant_recommendation(self):
        rec = _build_recommendation(70)
        assert "significant" in rec.lower() or "time limits" in rec.lower()

    def test_critical_recommendation(self):
        rec = _build_recommendation(90)
        assert "critical" in rec.lower() or "psychologist" in rec.lower()


class TestCalculateDependencyScore:
    """Test the main score calculation function."""

    @pytest.mark.asyncio
    async def test_no_events_returns_zero(self, test_session, group_with_member):
        group, member = group_with_member
        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.score == 0
        assert score.trend == "stable"
        assert score.risk_factors == []
        assert score.platform_breakdown == {}

    @pytest.mark.asyncio
    async def test_non_companion_events_ignored(self, test_session, group_with_member):
        """Events on non-companion platforms (chatgpt, etc.) don't count."""
        group, member = group_with_member
        for _ in range(10):
            test_session.add(_make_capture_event(group, member, platform="chatgpt"))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.score == 0

    @pytest.mark.asyncio
    async def test_companion_events_counted(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)
        # Create enough events to register a frequency score (>1/day over 7 days)
        for i in range(20):
            test_session.add(_make_capture_event(
                group, member,
                platform="characterai",
                timestamp=now - timedelta(hours=i * 2),
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id, days=7)
        assert score.score > 0
        assert "characterai" in score.platform_breakdown

    @pytest.mark.asyncio
    async def test_multiple_platforms_tracked(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)
        test_session.add(_make_capture_event(group, member, platform="characterai", timestamp=now))
        test_session.add(_make_capture_event(group, member, platform="replika", timestamp=now - timedelta(hours=1)))
        test_session.add(_make_capture_event(group, member, platform="pi", timestamp=now - timedelta(hours=2)))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert "characterai" in score.platform_breakdown
        assert "replika" in score.platform_breakdown
        assert "pi" in score.platform_breakdown

    @pytest.mark.asyncio
    async def test_late_night_increases_time_score(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)
        for i in range(10):
            late_time = now.replace(hour=23, minute=0) - timedelta(days=i)
            test_session.add(_make_capture_event(
                group, member,
                platform="replika",
                timestamp=late_time,
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.time_pattern_score > 0

    @pytest.mark.asyncio
    async def test_session_duration_with_multiple_events(self, test_session, group_with_member):
        """Multi-event sessions should estimate duration from first to last event."""
        group, member = group_with_member
        now = datetime.now(timezone.utc)
        session_id = "long-session-1"
        test_session.add(_make_capture_event(
            group, member, platform="characterai",
            session_id=session_id,
            timestamp=now - timedelta(minutes=45),
        ))
        test_session.add(_make_capture_event(
            group, member, platform="characterai",
            session_id=session_id,
            timestamp=now,
        ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.session_duration_score >= 15

    @pytest.mark.asyncio
    async def test_attachment_language_score_from_risk_events(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)

        for i in range(10):
            test_session.add(_make_capture_event(
                group, member,
                platform="characterai",
                timestamp=now - timedelta(hours=i),
            ))

        for i in range(5):
            test_session.add(RiskEvent(
                id=uuid.uuid4(),
                group_id=group.id,
                member_id=member.id,
                category="EMOTIONAL_DEPENDENCY",
                severity="medium",
                confidence=0.85,
                classifier_source="keyword",
                acknowledged=False,
                created_at=now - timedelta(hours=i),
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.attachment_language_score > 0


class TestTrendDetection:
    """Test trend calculation logic."""

    @pytest.mark.asyncio
    async def test_worsening_trend(self, test_session, group_with_member):
        """More recent events than older ones = worsening."""
        group, member = group_with_member
        now = datetime.now(timezone.utc)

        for i in range(10):
            test_session.add(_make_capture_event(
                group, member,
                platform="characterai",
                timestamp=now - timedelta(days=i),
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id, days=30)
        assert score.trend == "worsening"

    @pytest.mark.asyncio
    async def test_improving_trend(self, test_session, group_with_member):
        """More older events than recent = improving."""
        group, member = group_with_member
        now = datetime.now(timezone.utc)

        for i in range(10):
            test_session.add(_make_capture_event(
                group, member,
                platform="characterai",
                timestamp=now - timedelta(days=20 + i % 5),
            ))
        test_session.add(_make_capture_event(
            group, member,
            platform="characterai",
            timestamp=now - timedelta(days=1),
        ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id, days=30)
        assert score.trend == "improving"


class TestThresholdAlerts:
    """Test alert creation at thresholds."""

    @pytest.mark.asyncio
    async def test_no_alerts_for_low_score(self, test_session, group_with_member):
        group, member = group_with_member
        result = await check_dependency_alerts(test_session, group.id)
        assert result["alerts_created"] == 0

    def test_companion_platforms_constant(self):
        assert "characterai" in COMPANION_PLATFORMS
        assert "replika" in COMPANION_PLATFORMS
        assert "pi" in COMPANION_PLATFORMS
        assert "chatgpt" not in COMPANION_PLATFORMS

    def test_threshold_values(self):
        assert ALERT_THRESHOLD == 60
        assert CRITICAL_THRESHOLD == 80
        assert CRITICAL_THRESHOLD > ALERT_THRESHOLD


class TestEdgeCases:
    """Test edge cases for score calculation."""

    @pytest.mark.asyncio
    async def test_single_event(self, test_session, group_with_member):
        group, member = group_with_member
        test_session.add(_make_capture_event(
            group, member,
            platform="pi",
            timestamp=datetime.now(timezone.utc),
        ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert isinstance(score, DependencyScore)
        assert 0 <= score.score <= 100

    @pytest.mark.asyncio
    async def test_score_never_exceeds_100(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)

        for i in range(100):
            test_session.add(_make_capture_event(
                group, member,
                platform="characterai",
                timestamp=now.replace(hour=23) - timedelta(hours=i),
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        assert score.score <= 100

    @pytest.mark.asyncio
    async def test_custom_days_parameter(self, test_session, group_with_member):
        group, member = group_with_member
        score = await calculate_dependency_score(test_session, group.id, member.id, days=7)
        assert isinstance(score, DependencyScore)
        assert score.score == 0

    @pytest.mark.asyncio
    async def test_score_components_sum_correctly(self, test_session, group_with_member):
        group, member = group_with_member
        now = datetime.now(timezone.utc)
        for i in range(5):
            test_session.add(_make_capture_event(
                group, member,
                platform="replika",
                timestamp=now - timedelta(hours=i),
            ))
        await test_session.flush()

        score = await calculate_dependency_score(test_session, group.id, member.id)
        expected = (
            score.session_duration_score
            + score.frequency_score
            + score.attachment_language_score
            + score.time_pattern_score
        )
        assert score.score == expected
