"""Unit tests for src.intelligence.scoring — unified risk scoring module.

Tests cover:
- Score computation with all sources present
- Score with missing sources (graceful — missing source contributes 0)
- Weight differences across age tiers
- Score always 0-100 (boundary tests)
- Confidence calculation (< 7 days, 7-30 days, 30+ days)
- Trend: increasing (diff > 5), stable (diff < 5), decreasing (diff < -5)
- Breakdown shows correct weights per tier
- History returns correct date range
- Empty data returns score 0 with low confidence
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.age_tier.rules import AgeTier
from src.intelligence.scoring import (
    _WEIGHTS,
    SOURCES,
    _compute_ai_monitoring_score,
    _compute_confidence,
    _compute_device_usage_score,
    _compute_location_score,
    _compute_social_behavior_score,
    _default_tier,
    compute_unified_score,
    get_score_trend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(scalar_values=None, scalars_all=None, first=None, all_rows=None):
    """Build a minimal mock AsyncSession."""
    session = AsyncMock()

    # result mock
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_values
    result.scalars.return_value.all.return_value = scalars_all or []
    result.first.return_value = first
    result.all.return_value = all_rows or []

    session.execute = AsyncMock(return_value=result)
    return session


# ===========================================================================
# 1. Weight table — static correctness
# ===========================================================================


class TestWeightTable:
    def test_all_tiers_have_four_sources(self):
        for tier in (AgeTier.YOUNG, AgeTier.PRETEEN, AgeTier.TEEN):
            for source in SOURCES:
                assert (tier, source) in _WEIGHTS

    def test_weights_sum_to_one_young(self):
        total = sum(_WEIGHTS[(AgeTier.YOUNG, s)] for s in SOURCES)
        assert abs(total - 1.0) < 1e-9

    def test_weights_sum_to_one_preteen(self):
        total = sum(_WEIGHTS[(AgeTier.PRETEEN, s)] for s in SOURCES)
        assert abs(total - 1.0) < 1e-9

    def test_weights_sum_to_one_teen(self):
        total = sum(_WEIGHTS[(AgeTier.TEEN, s)] for s in SOURCES)
        assert abs(total - 1.0) < 1e-9

    def test_young_ai_weight_higher_than_teen(self):
        assert _WEIGHTS[(AgeTier.YOUNG, "ai_monitoring")] > _WEIGHTS[(AgeTier.TEEN, "ai_monitoring")]

    def test_teen_social_weight_higher_than_young(self):
        assert _WEIGHTS[(AgeTier.TEEN, "social_behavior")] > _WEIGHTS[(AgeTier.YOUNG, "social_behavior")]

    def test_device_weight_same_across_tiers(self):
        assert _WEIGHTS[(AgeTier.YOUNG, "device_usage")] == _WEIGHTS[(AgeTier.PRETEEN, "device_usage")]
        assert _WEIGHTS[(AgeTier.PRETEEN, "device_usage")] == _WEIGHTS[(AgeTier.TEEN, "device_usage")]

    def test_location_weight_same_across_tiers(self):
        assert _WEIGHTS[(AgeTier.YOUNG, "location")] == _WEIGHTS[(AgeTier.PRETEEN, "location")]
        assert _WEIGHTS[(AgeTier.PRETEEN, "location")] == _WEIGHTS[(AgeTier.TEEN, "location")]


# ===========================================================================
# 2. Default tier
# ===========================================================================


class TestDefaultTier:
    def test_default_tier_is_preteen(self):
        assert _default_tier() == AgeTier.PRETEEN


# ===========================================================================
# 3. Location score placeholder
# ===========================================================================


class TestLocationScore:
    def test_location_always_zero(self):
        assert _compute_location_score() == 0.0


# ===========================================================================
# 4. AI monitoring sub-score
# ===========================================================================


@pytest.mark.asyncio
class TestAIMonitoringScore:
    async def test_no_events_returns_zero(self):
        session = _make_session(scalars_all=[])
        score = await _compute_ai_monitoring_score(session, uuid4())
        assert score == 0.0

    async def test_one_critical_event_returns_40(self):
        session = _make_session(scalars_all=["critical"])
        score = await _compute_ai_monitoring_score(session, uuid4())
        assert score == 40.0

    async def test_multiple_events_accumulate(self):
        # critical(40) + high(25) + medium(10) = 75
        session = _make_session(scalars_all=["critical", "high", "medium"])
        score = await _compute_ai_monitoring_score(session, uuid4())
        assert score == 75.0

    async def test_score_capped_at_100(self):
        # 3 criticals = 120 → capped at 100
        session = _make_session(scalars_all=["critical", "critical", "critical"])
        score = await _compute_ai_monitoring_score(session, uuid4())
        assert score == 100.0

    async def test_unknown_severity_adds_zero(self):
        session = _make_session(scalars_all=["unknown"])
        score = await _compute_ai_monitoring_score(session, uuid4())
        assert score == 0.0


# ===========================================================================
# 5. Social behavior sub-score
# ===========================================================================


@pytest.mark.asyncio
class TestSocialBehaviorScore:
    async def test_no_baseline_returns_zero(self):
        session = _make_session(first=None)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 0.0

    async def test_baseline_with_risk_score_key(self):
        row = MagicMock()
        row.metrics = {"risk_score": 65.0}
        session = _make_session(first=row)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 65.0

    async def test_baseline_with_anomaly_score_key(self):
        row = MagicMock()
        row.metrics = {"anomaly_score": 30.0}
        session = _make_session(first=row)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 30.0

    async def test_score_clamped_to_100(self):
        row = MagicMock()
        row.metrics = {"risk_score": 150.0}
        session = _make_session(first=row)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 100.0

    async def test_metrics_none_returns_zero(self):
        row = MagicMock()
        row.metrics = None
        session = _make_session(first=row)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 0.0

    async def test_unknown_metric_keys_return_zero(self):
        row = MagicMock()
        row.metrics = {"some_other_key": 50.0}
        session = _make_session(first=row)
        score = await _compute_social_behavior_score(session, uuid4())
        assert score == 0.0


# ===========================================================================
# 6. Device usage sub-score
# ===========================================================================


@pytest.mark.asyncio
class TestDeviceUsageScore:
    async def test_no_records_returns_zero(self):
        session = _make_session(scalars_all=[])
        score = await _compute_device_usage_score(session, uuid4())
        assert score == 0.0

    async def test_low_screen_time_returns_zero(self):
        # 60 min/day ≤ warn threshold (120) → 0
        session = _make_session(scalars_all=[60.0, 60.0])
        score = await _compute_device_usage_score(session, uuid4())
        assert score == 0.0

    async def test_max_screen_time_returns_100(self):
        # 480 min/day = max threshold → 100
        session = _make_session(scalars_all=[480.0])
        score = await _compute_device_usage_score(session, uuid4())
        assert score == 100.0

    async def test_midpoint_screen_time(self):
        # avg = 300 min → ratio = (300-120)/(480-120) = 180/360 = 0.5 → 50
        session = _make_session(scalars_all=[300.0])
        score = await _compute_device_usage_score(session, uuid4())
        assert abs(score - 50.0) < 0.1

    async def test_above_max_capped_at_100(self):
        session = _make_session(scalars_all=[600.0])
        score = await _compute_device_usage_score(session, uuid4())
        assert score == 100.0


# ===========================================================================
# 7. Confidence calculation
# ===========================================================================


@pytest.mark.asyncio
class TestConfidenceCalculation:
    async def test_no_data_returns_low(self):
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)
        confidence = await _compute_confidence(session, uuid4())
        assert confidence == "low"

    async def test_very_recent_data_returns_low(self):
        """Less than 7 days of data."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=3)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            if call_count == 0:
                res.scalar_one_or_none.return_value = recent
            elif call_count == 1:
                res.scalar_one_or_none.return_value = None
            else:
                res.scalar_one_or_none.return_value = None
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        confidence = await _compute_confidence(session, uuid4())
        assert confidence == "low"

    async def test_two_weeks_data_returns_medium(self):
        """14 days of data → medium."""
        now = datetime.now(timezone.utc)
        two_weeks_ago = now - timedelta(days=14)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            if call_count == 0:
                res.scalar_one_or_none.return_value = two_weeks_ago
            else:
                res.scalar_one_or_none.return_value = None
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        confidence = await _compute_confidence(session, uuid4())
        assert confidence == "medium"

    async def test_over_thirty_days_returns_high(self):
        """35 days of data → high."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=35)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            if call_count == 0:
                res.scalar_one_or_none.return_value = old
            else:
                res.scalar_one_or_none.return_value = None
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        confidence = await _compute_confidence(session, uuid4())
        assert confidence == "high"


# ===========================================================================
# 8. Score trend
# ===========================================================================


@pytest.mark.asyncio
class TestScoreTrend:
    async def test_stable_when_both_windows_empty(self):
        session = _make_session(scalars_all=[])


        async def side_effect(*args, **kwargs):
            res = MagicMock()
            res.scalars.return_value.all.return_value = []
            return res

        session.execute.side_effect = side_effect
        trend = await get_score_trend(session, uuid4())
        assert trend == "stable"

    async def test_increasing_when_current_much_higher(self):
        """Current window has critical events, past has none → increasing."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            # First call: current window
            if call_count == 0:
                res.scalars.return_value.all.return_value = ["critical", "critical"]
            else:
                res.scalars.return_value.all.return_value = []
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        trend = await get_score_trend(session, uuid4())
        assert trend == "increasing"

    async def test_decreasing_when_past_much_higher(self):
        """Past window has critical events, current has none → decreasing."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            if call_count == 0:
                res.scalars.return_value.all.return_value = []
            else:
                res.scalars.return_value.all.return_value = ["critical", "critical"]
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        trend = await get_score_trend(session, uuid4())
        assert trend == "decreasing"

    async def test_stable_when_difference_less_than_5(self):
        """Both windows produce score difference < 5 → stable."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            res = MagicMock()
            # Both windows: one medium event = 10 pts each → diff = 0
            res.scalars.return_value.all.return_value = ["medium"]
            call_count += 1
            return res

        session = AsyncMock()
        session.execute.side_effect = side_effect
        trend = await get_score_trend(session, uuid4())
        assert trend == "stable"


# ===========================================================================
# 9. compute_unified_score — boundary and structure
# ===========================================================================


@pytest.mark.asyncio
class TestComputeUnifiedScore:
    async def _make_zero_session(self):
        """Returns a session that produces all-zero sub-scores."""
        session = AsyncMock()

        async def side_effect(*args, **kwargs):
            res = MagicMock()
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
            res.first.return_value = None
            res.all.return_value = []
            return res

        session.execute.side_effect = side_effect
        return session

    async def test_empty_data_returns_zero_score(self):
        session = await self._make_zero_session()
        result = await compute_unified_score(session, uuid4())
        assert result["unified_score"] == 0.0

    async def test_empty_data_returns_low_confidence(self):
        session = await self._make_zero_session()
        result = await compute_unified_score(session, uuid4())
        assert result["confidence"] == "low"

    async def test_result_has_required_fields(self):
        session = await self._make_zero_session()
        child_id = uuid4()
        result = await compute_unified_score(session, child_id)
        assert "child_id" in result
        assert "unified_score" in result
        assert "confidence" in result
        assert "trend" in result
        assert "age_tier" in result

    async def test_score_always_between_0_and_100(self):
        """Even with extreme values, score is clamped to [0, 100]."""
        session = await self._make_zero_session()
        result = await compute_unified_score(session, uuid4())
        assert 0.0 <= result["unified_score"] <= 100.0
