"""Unit tests for the safety score calculation service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups.models import GroupMember
from src.risk.models import RiskEvent
from src.risk.score import (
    SEVERITY_WEIGHTS,
    _compute_raw_penalty,
    _normalize_score,
    _recency_decay,
    calculate_group_score,
    calculate_member_score,
    get_score_history,
)
from tests.conftest import make_test_group


def _make_risk_event(
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    severity: str = "medium",
    category: str = "SELF_HARM",
    days_ago: float = 0,
) -> RiskEvent:
    """Create a RiskEvent instance for testing."""
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return RiskEvent(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        category=category,
        severity=severity,
        confidence=0.9,
        classifier_source="keyword",
        details={"reasoning": "test"},
        acknowledged=False,
        created_at=created,
        updated_at=created,
    )


@pytest_asyncio.fixture
async def group_and_member(test_session: AsyncSession):
    """Create a test group with a member."""
    group, owner_id = await make_test_group(test_session)

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=owner_id,
        role="member",
        display_name="Test Child",
    )
    test_session.add(member)
    await test_session.flush()

    return group, member


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestRecencyDecay:
    def test_day_zero_weight_is_one(self):
        assert _recency_decay(0) == pytest.approx(1.0)

    def test_older_events_have_lower_weight(self):
        assert _recency_decay(7) < _recency_decay(0)
        assert _recency_decay(30) < _recency_decay(7)

    def test_weight_never_negative(self):
        assert _recency_decay(365) > 0


class TestNormalizeScore:
    def test_zero_penalty_gives_100(self):
        assert _normalize_score(0) == 100.0

    def test_high_penalty_gives_low_score(self):
        assert _normalize_score(500) < 20

    def test_moderate_penalty(self):
        score = _normalize_score(100)
        assert 45 <= score <= 55

    def test_score_within_bounds(self):
        for penalty in [0, 10, 50, 100, 200, 500, 1000]:
            score = _normalize_score(penalty)
            assert 0 <= score <= 100


class TestComputeRawPenalty:
    def test_no_events_zero_penalty(self):
        now = datetime.now(timezone.utc)
        assert _compute_raw_penalty([], now) == 0.0

    def test_critical_weighs_more_than_low(self):
        now = datetime.now(timezone.utc)
        gid = uuid.uuid4()
        mid = uuid.uuid4()

        critical_event = _make_risk_event(gid, mid, severity="critical", days_ago=0)
        low_event = _make_risk_event(gid, mid, severity="low", days_ago=0)

        critical_penalty = _compute_raw_penalty([critical_event], now)
        low_penalty = _compute_raw_penalty([low_event], now)

        assert critical_penalty > low_penalty
        assert critical_penalty == pytest.approx(SEVERITY_WEIGHTS["critical"], rel=0.01)
        assert low_penalty == pytest.approx(SEVERITY_WEIGHTS["low"], rel=0.01)

    def test_older_events_contribute_less(self):
        now = datetime.now(timezone.utc)
        gid = uuid.uuid4()
        mid = uuid.uuid4()

        recent = _make_risk_event(gid, mid, severity="high", days_ago=0)
        old = _make_risk_event(gid, mid, severity="high", days_ago=20)

        recent_penalty = _compute_raw_penalty([recent], now)
        old_penalty = _compute_raw_penalty([old], now)

        assert recent_penalty > old_penalty


# ---------------------------------------------------------------------------
# Database-backed score calculation tests
# ---------------------------------------------------------------------------


class TestCalculateMemberScore:
    @pytest.mark.asyncio
    async def test_no_events_gives_perfect_score(self, test_session, group_and_member):
        group, member = group_and_member
        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.score == 100.0
        assert result.trend == "stable"
        assert result.top_categories == []
        assert result.risk_count_by_severity == {
            "critical": 0, "high": 0, "medium": 0, "low": 0,
        }

    @pytest.mark.asyncio
    async def test_single_critical_lowers_score(self, test_session, group_and_member):
        group, member = group_and_member
        event = _make_risk_event(group.id, member.id, severity="critical", days_ago=0)
        test_session.add(event)
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.score < 100.0
        assert result.risk_count_by_severity["critical"] == 1

    @pytest.mark.asyncio
    async def test_many_criticals_very_low_score(self, test_session, group_and_member):
        group, member = group_and_member
        for i in range(10):
            event = _make_risk_event(group.id, member.id, severity="critical", days_ago=i)
            test_session.add(event)
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.score < 30.0
        assert result.risk_count_by_severity["critical"] == 10

    @pytest.mark.asyncio
    async def test_only_low_events_high_score(self, test_session, group_and_member):
        group, member = group_and_member
        for i in range(5):
            event = _make_risk_event(group.id, member.id, severity="low", days_ago=i)
            test_session.add(event)
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.score > 80.0

    @pytest.mark.asyncio
    async def test_top_categories_populated(self, test_session, group_and_member):
        group, member = group_and_member
        for _ in range(3):
            test_session.add(
                _make_risk_event(group.id, member.id, category="SELF_HARM", days_ago=0)
            )
        test_session.add(
            _make_risk_event(group.id, member.id, category="PII_EXPOSURE", days_ago=0)
        )
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.top_categories[0] == "SELF_HARM"
        assert "PII_EXPOSURE" in result.top_categories

    @pytest.mark.asyncio
    async def test_mixed_severities(self, test_session, group_and_member):
        group, member = group_and_member
        test_session.add(_make_risk_event(group.id, member.id, severity="critical", days_ago=0))
        test_session.add(_make_risk_event(group.id, member.id, severity="high", days_ago=1))
        test_session.add(_make_risk_event(group.id, member.id, severity="medium", days_ago=2))
        test_session.add(_make_risk_event(group.id, member.id, severity="low", days_ago=3))
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id)
        assert result.risk_count_by_severity == {
            "critical": 1, "high": 1, "medium": 1, "low": 1,
        }
        assert 0 < result.score < 100

    @pytest.mark.asyncio
    async def test_old_events_excluded_by_window(self, test_session, group_and_member):
        group, member = group_and_member
        # Event outside the default 30-day window
        event = _make_risk_event(group.id, member.id, severity="critical", days_ago=31)
        test_session.add(event)
        await test_session.flush()

        result = await calculate_member_score(test_session, group.id, member.id, days=30)
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_custom_days_window(self, test_session, group_and_member):
        group, member = group_and_member
        event = _make_risk_event(group.id, member.id, severity="critical", days_ago=5)
        test_session.add(event)
        await test_session.flush()

        result_7 = await calculate_member_score(test_session, group.id, member.id, days=7)
        result_3 = await calculate_member_score(test_session, group.id, member.id, days=3)

        assert result_7.score < 100.0
        assert result_3.score == 100.0  # Event outside 3-day window


class TestCalculateGroupScore:
    @pytest.mark.asyncio
    async def test_no_events_gives_perfect_group_score(self, test_session, group_and_member):
        group, member = group_and_member
        result = await calculate_group_score(test_session, group.id)
        assert result.average_score == 100.0
        assert result.member_scores == []

    @pytest.mark.asyncio
    async def test_group_score_averages_members(self, test_session, group_and_member):
        group, member = group_and_member

        # Create a second member
        user2_id = uuid.uuid4()
        from src.auth.models import User
        user2 = User(
            id=user2_id,
            email=f"test-{uuid.uuid4().hex[:8]}@example.com",
            display_name="Second User",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        test_session.add(user2)
        await test_session.flush()

        member2 = GroupMember(
            id=uuid.uuid4(),
            group_id=group.id,
            user_id=user2_id,
            role="member",
            display_name="Child 2",
        )
        test_session.add(member2)
        await test_session.flush()

        # Member 1 gets lots of critical events (low score)
        for i in range(5):
            test_session.add(
                _make_risk_event(group.id, member.id, severity="critical", days_ago=i)
            )
        # Member 2 gets one low event (high score)
        test_session.add(
            _make_risk_event(group.id, member2.id, severity="low", days_ago=0)
        )
        await test_session.flush()

        result = await calculate_group_score(test_session, group.id)
        assert len(result.member_scores) == 2
        # Average should be between the individual scores
        scores = [ms.score for ms in result.member_scores]
        assert min(scores) < result.average_score < max(scores)


class TestGetScoreHistory:
    @pytest.mark.asyncio
    async def test_no_events_all_perfect(self, test_session, group_and_member):
        group, member = group_and_member
        history = await get_score_history(test_session, group.id, member.id, days=7)
        assert len(history) == 8  # 7 days + today
        for entry in history:
            assert entry.score == 100.0

    @pytest.mark.asyncio
    async def test_history_has_dates(self, test_session, group_and_member):
        group, member = group_and_member
        history = await get_score_history(test_session, group.id, member.id, days=7)
        dates = [e.date for e in history]
        # Dates should be unique
        assert len(set(dates)) == len(dates)

    @pytest.mark.asyncio
    async def test_recent_event_lowers_recent_scores(self, test_session, group_and_member):
        group, member = group_and_member
        event = _make_risk_event(group.id, member.id, severity="critical", days_ago=0)
        test_session.add(event)
        await test_session.flush()

        history = await get_score_history(test_session, group.id, member.id, days=7)
        # Most recent score should be lower than oldest
        assert history[-1].score < 100.0
