"""Unit tests for behavioral anomaly correlation (P3-I4).

Tests cover:
- Multi-signal deviation detection
- Evasion detection (AI drop + screen time stable)
- Cross-signal anomaly patterns
- run_anomaly_scan summary
- Edge cases: empty baseline, single data point
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.device_agent.models import ScreenTimeRecord
from src.groups.models import GroupMember
from src.intelligence.anomaly import (
    _deviation_factor,
    _safe_mean,
    _safe_std,
    compute_multi_signal_deviation,
    detect_cross_signal_anomalies,
    detect_evasion,
    run_anomaly_scan,
    SIGNAL_AI_USAGE,
    SIGNAL_SCREEN_TIME,
    SIGNAL_SOCIAL_ACTIVITY,
)
from src.intelligence.models import BehavioralBaseline
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_safe_mean_empty():
    assert _safe_mean([]) == 0.0


def test_safe_mean_values():
    assert _safe_mean([2.0, 4.0, 6.0]) == 4.0


def test_safe_std_empty():
    assert _safe_std([]) == 0.0


def test_safe_std_single():
    assert _safe_std([5.0]) == 0.0


def test_safe_std_uniform():
    assert _safe_std([3.0, 3.0, 3.0]) == 0.0


def test_safe_std_known_values():
    # [2, 4, 4, 4, 5, 5, 7, 9] -> population std = 2.0
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    assert abs(_safe_std(values) - 2.0) < 0.01


def test_deviation_factor_normal():
    # (6 - 4) / 2 = 1.0
    assert _deviation_factor(6.0, 4.0, 2.0) == pytest.approx(1.0)


def test_deviation_factor_below_mean():
    # (2 - 4) / 2 = -1.0
    assert _deviation_factor(2.0, 4.0, 2.0) == pytest.approx(-1.0)


def test_deviation_factor_zero_std_above():
    dev = _deviation_factor(5.0, 3.0, 0.0)
    # Capped at 99.0 (not inf) to stay JSON-serializable
    assert dev == 99.0


def test_deviation_factor_zero_std_equal():
    assert _deviation_factor(3.0, 3.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_member(session, group) -> GroupMember:
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="TestChild",
    )
    session.add(member)
    await session.flush()
    return member


async def _add_baseline(session, member_id, metrics: dict, days_ago: int = 0):
    """Add a BehavioralBaseline row with given metrics, computed days_ago."""
    computed = datetime.now(timezone.utc) - timedelta(days=days_ago)
    b = BehavioralBaseline(
        id=uuid4(),
        member_id=member_id,
        window_days=30,
        metrics=metrics,
        computed_at=computed,
        sample_count=10,
    )
    session.add(b)
    await session.flush()
    return b


async def _add_screen_time(session, member, group, minutes: float, days_ago: int = 0):
    """Add a ScreenTimeRecord row."""
    d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date()
    rec = ScreenTimeRecord(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        date=d,
        total_minutes=minutes,
        pickups=0,
    )
    session.add(rec)
    await session.flush()
    return rec


# ---------------------------------------------------------------------------
# compute_multi_signal_deviation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deviation_empty_baseline_no_crash(test_session):
    """No baseline data returns only location placeholder, no crash."""
    group, _ = await make_test_group(test_session, name="G1", group_type="family")
    member = await _make_member(test_session, group)

    results = await compute_multi_signal_deviation(test_session, member.id)

    # Should not raise; returns at least the location placeholder
    assert isinstance(results, list)
    # Only the location placeholder expected (no AI or social data)
    location_sigs = [r for r in results if r["signal_type"] == "location_movement"]
    assert len(location_sigs) == 1
    assert location_sigs[0]["is_anomalous"] is False


@pytest.mark.asyncio
async def test_deviation_single_baseline_no_anomaly(test_session):
    """Single baseline point is insufficient data — no AI signal entry produced."""
    group, _ = await make_test_group(test_session, name="G2", group_type="family")
    member = await _make_member(test_session, group)

    await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=1)

    results = await compute_multi_signal_deviation(test_session, member.id)
    ai_sigs = [r for r in results if r["signal_type"] == SIGNAL_AI_USAGE]
    # With only 1 baseline snapshot, the implementation skips the signal (insufficient data).
    # The spec requires: "Single data point returns no anomalies (insufficient data)"
    assert len(ai_sigs) == 0


@pytest.mark.asyncio
async def test_deviation_normal_behavior_no_flag(test_session):
    """Values within 1σ should not be flagged as anomalous."""
    group, _ = await make_test_group(test_session, name="G3", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline: 5 sessions/day, std ~0.5. Current: 5.3 (within 1σ)
    for i in range(1, 6):
        await _add_baseline(
            test_session, member.id, {"ai_session_count": float(5 + (i % 2) * 0.5)}, days_ago=i
        )
    # Most recent (current)
    await _add_baseline(test_session, member.id, {"ai_session_count": 5.3}, days_ago=0)

    results = await compute_multi_signal_deviation(test_session, member.id)
    ai_sigs = [r for r in results if r["signal_type"] == SIGNAL_AI_USAGE]
    assert len(ai_sigs) == 1
    assert ai_sigs[0]["is_anomalous"] is False


@pytest.mark.asyncio
async def test_deviation_above_2sigma_flagged(test_session):
    """Value more than 2σ above mean should be flagged."""
    group, _ = await make_test_group(test_session, name="G4", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline: ai_usage=5 daily, std=1 (values 4,5,5,6,5 → mean=5, std~0.63)
    baseline_values = [4.0, 5.0, 5.0, 6.0, 5.0]
    for i, val in enumerate(baseline_values):
        await _add_baseline(
            test_session, member.id, {"ai_session_count": val}, days_ago=i + 1
        )
    # Current: 15 sessions — way above 2σ
    await _add_baseline(test_session, member.id, {"ai_session_count": 15.0}, days_ago=0)

    results = await compute_multi_signal_deviation(test_session, member.id)
    ai_sigs = [r for r in results if r["signal_type"] == SIGNAL_AI_USAGE]
    assert len(ai_sigs) == 1
    assert ai_sigs[0]["is_anomalous"] is True
    assert ai_sigs[0]["deviation_factor"] > 2.0
    assert ai_sigs[0]["current_value"] == 15.0


@pytest.mark.asyncio
async def test_deviation_below_2sigma_not_flagged(test_session):
    """Value within 2σ should NOT be flagged."""
    group, _ = await make_test_group(test_session, name="G5", group_type="family")
    member = await _make_member(test_session, group)

    for i in range(1, 6):
        await _add_baseline(test_session, member.id, {"ai_session_count": 10.0}, days_ago=i)
    # Current: 11 — only slightly above mean (std=0, so if exactly mean → no flag)
    # Let's use varied baseline so std > 0
    await _add_baseline(test_session, member.id, {"ai_session_count": 8.0}, days_ago=6)
    await _add_baseline(test_session, member.id, {"ai_session_count": 12.0}, days_ago=7)
    # Current: 10.5 (well within σ range)
    await _add_baseline(test_session, member.id, {"ai_session_count": 10.5}, days_ago=0)

    results = await compute_multi_signal_deviation(test_session, member.id)
    ai_sigs = [r for r in results if r["signal_type"] == SIGNAL_AI_USAGE]
    assert len(ai_sigs) == 1
    assert ai_sigs[0]["is_anomalous"] is False


@pytest.mark.asyncio
async def test_deviation_screen_time_flagged(test_session):
    """Screen time spike >2σ should be flagged."""
    group, _ = await make_test_group(test_session, name="G6", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline: ~60 min/day for 5 days
    for i in range(1, 6):
        await _add_screen_time(test_session, member, group, minutes=60.0, days_ago=i)
    # Spike: 600 min today
    await _add_screen_time(test_session, member, group, minutes=600.0, days_ago=0)

    results = await compute_multi_signal_deviation(test_session, member.id)
    st_sigs = [r for r in results if r["signal_type"] == SIGNAL_SCREEN_TIME]
    assert len(st_sigs) == 1
    assert st_sigs[0]["is_anomalous"] is True


@pytest.mark.asyncio
async def test_deviation_result_structure(test_session):
    """Result dicts have all required keys."""
    group, _ = await make_test_group(test_session, name="G7", group_type="family")
    member = await _make_member(test_session, group)

    await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=1)
    await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=0)

    results = await compute_multi_signal_deviation(test_session, member.id)
    for r in results:
        assert "signal_type" in r
        assert "current_value" in r
        assert "mean" in r
        assert "stddev" in r
        assert "deviation_factor" in r
        assert "is_anomalous" in r


# ---------------------------------------------------------------------------
# detect_evasion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evasion_ai_drop_screen_stable(test_session):
    """AI usage drops >50% while screen time stays stable → evasion flagged."""
    group, _ = await make_test_group(test_session, name="EV1", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline AI: 20 sessions/day for 5 days
    for i in range(1, 6):
        await _add_baseline(test_session, member.id, {"ai_session_count": 20.0}, days_ago=i)
    # Current AI: 5 sessions (75% drop)
    await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=0)

    # Screen time: stable ~120 min/day
    for i in range(1, 6):
        await _add_screen_time(test_session, member, group, minutes=120.0, days_ago=i)
    await _add_screen_time(test_session, member, group, minutes=125.0, days_ago=0)

    result = await detect_evasion(test_session, member.id)

    assert result is not None
    assert result["ai_drop_pct"] > 0.5
    assert result["confidence"] in ("low", "medium", "high")
    assert "reason" in result
    assert "child_id" in result


@pytest.mark.asyncio
async def test_evasion_ai_drop_screen_also_drops(test_session):
    """AI usage drops AND screen time drops → NOT evasion (legitimate reduction)."""
    group, _ = await make_test_group(test_session, name="EV2", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline AI: 20 sessions/day
    for i in range(1, 6):
        await _add_baseline(test_session, member.id, {"ai_session_count": 20.0}, days_ago=i)
    # Current AI: 5 sessions (75% drop)
    await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=0)

    # Screen time also dropped: 120 → 30 min (~75% drop)
    for i in range(1, 6):
        await _add_screen_time(test_session, member, group, minutes=120.0, days_ago=i)
    await _add_screen_time(test_session, member, group, minutes=30.0, days_ago=0)

    result = await detect_evasion(test_session, member.id)
    assert result is None


@pytest.mark.asyncio
async def test_evasion_small_ai_drop_not_flagged(test_session):
    """AI usage drops <50% → evasion NOT flagged."""
    group, _ = await make_test_group(test_session, name="EV3", group_type="family")
    member = await _make_member(test_session, group)

    for i in range(1, 4):
        await _add_baseline(test_session, member.id, {"ai_session_count": 10.0}, days_ago=i)
    # Drop from 10 to 7 (30% drop — below 50% threshold)
    await _add_baseline(test_session, member.id, {"ai_session_count": 7.0}, days_ago=0)

    for i in range(1, 4):
        await _add_screen_time(test_session, member, group, minutes=120.0, days_ago=i)
    await _add_screen_time(test_session, member, group, minutes=120.0, days_ago=0)

    result = await detect_evasion(test_session, member.id)
    assert result is None


@pytest.mark.asyncio
async def test_evasion_no_baseline_returns_none(test_session):
    """No baseline data → detect_evasion returns None."""
    member_id = uuid4()
    result = await detect_evasion(test_session, member_id)
    assert result is None


@pytest.mark.asyncio
async def test_evasion_insufficient_baseline_returns_none(test_session):
    """Only 1 AI baseline snapshot → cannot compare, returns None."""
    group, _ = await make_test_group(test_session, name="EV5", group_type="family")
    member = await _make_member(test_session, group)

    await _add_baseline(test_session, member.id, {"ai_session_count": 10.0}, days_ago=0)
    await _add_screen_time(test_session, member, group, minutes=120.0, days_ago=0)

    result = await detect_evasion(test_session, member.id)
    assert result is None


# ---------------------------------------------------------------------------
# detect_cross_signal_anomalies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_signal_social_withdrawal_ai_spike(test_session):
    """Social withdrawal + AI usage spike → cross-signal anomaly flagged."""
    group, _ = await make_test_group(test_session, name="CS1", group_type="family")
    member = await _make_member(test_session, group)

    # Baseline: social=10, ai=5 for 5 days
    for i in range(1, 6):
        await _add_baseline(
            test_session, member.id,
            {"ai_session_count": 5.0, "avg_posts_per_day": 10.0},
            days_ago=i,
        )
    # Current: AI spiked to 30, social dropped to 1
    await _add_baseline(
        test_session, member.id,
        {"ai_session_count": 30.0, "avg_posts_per_day": 1.0},
        days_ago=0,
    )

    anomalies = await detect_cross_signal_anomalies(test_session, member.id)

    assert len(anomalies) >= 1
    patterns = [a["pattern_type"] for a in anomalies]
    assert "social_withdrawal_ai_spike" in patterns
    withdrawal = next(a for a in anomalies if a["pattern_type"] == "social_withdrawal_ai_spike")
    assert "signals" in withdrawal
    assert SIGNAL_AI_USAGE in withdrawal["signals"]
    assert SIGNAL_SOCIAL_ACTIVITY in withdrawal["signals"]
    assert withdrawal["severity"] in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_cross_signal_normal_not_flagged(test_session):
    """Normal social activity and normal AI usage → no cross-signal anomaly."""
    group, _ = await make_test_group(test_session, name="CS2", group_type="family")
    member = await _make_member(test_session, group)

    for i in range(1, 6):
        await _add_baseline(
            test_session, member.id,
            {"ai_session_count": 5.0, "avg_posts_per_day": 8.0},
            days_ago=i,
        )
    # Current: similar values — no spike or withdrawal
    await _add_baseline(
        test_session, member.id,
        {"ai_session_count": 5.5, "avg_posts_per_day": 7.5},
        days_ago=0,
    )

    anomalies = await detect_cross_signal_anomalies(test_session, member.id)
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_cross_signal_empty_baseline_returns_empty(test_session):
    """No baseline data returns empty list (no crash)."""
    member_id = uuid4()
    anomalies = await detect_cross_signal_anomalies(test_session, member_id)
    assert anomalies == []


@pytest.mark.asyncio
async def test_cross_signal_result_structure(test_session):
    """Cross-signal anomaly dicts have required keys."""
    group, _ = await make_test_group(test_session, name="CS3", group_type="family")
    member = await _make_member(test_session, group)

    for i in range(1, 6):
        await _add_baseline(
            test_session, member.id,
            {"ai_session_count": 5.0, "avg_posts_per_day": 10.0},
            days_ago=i,
        )
    await _add_baseline(
        test_session, member.id,
        {"ai_session_count": 40.0, "avg_posts_per_day": 0.0},
        days_ago=0,
    )

    anomalies = await detect_cross_signal_anomalies(test_session, member.id)
    for a in anomalies:
        assert "pattern_type" in a
        assert "signals" in a
        assert "description" in a
        assert "severity" in a
        assert "details" in a


# ---------------------------------------------------------------------------
# run_anomaly_scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scan_returns_summary(test_session):
    """run_anomaly_scan returns a dict with all expected top-level keys."""
    group, _ = await make_test_group(test_session, name="SC1", group_type="family")
    member = await _make_member(test_session, group)

    result = await run_anomaly_scan(test_session, member.id)

    assert "child_id" in result
    assert "scanned_at" in result
    assert "signal_anomalies" in result
    assert "evasion" in result
    assert "cross_signal_anomalies" in result
    assert "total_anomalies" in result
    assert "alerts_created" in result
    assert result["child_id"] == str(member.id)


@pytest.mark.asyncio
async def test_run_scan_no_data_total_zero(test_session):
    """Scan on child with no data returns 0 total_anomalies."""
    group, _ = await make_test_group(test_session, name="SC2", group_type="family")
    member = await _make_member(test_session, group)

    result = await run_anomaly_scan(test_session, member.id)
    assert result["total_anomalies"] == 0


@pytest.mark.asyncio
async def test_run_scan_counts_anomalies(test_session):
    """Scan summary total_anomalies sums flagged signals + evasion + cross-signal."""
    group, _ = await make_test_group(test_session, name="SC3", group_type="family")
    member = await _make_member(test_session, group)

    # Set up a deviation (AI spike)
    for i in range(1, 6):
        await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=i)
    await _add_baseline(test_session, member.id, {"ai_session_count": 50.0}, days_ago=0)

    result = await run_anomaly_scan(test_session, member.id)
    assert result["total_anomalies"] >= 1


@pytest.mark.asyncio
async def test_run_scan_creates_alerts(test_session):
    """Scan creates alerts for anomalies and reports alerts_created count."""
    group, _ = await make_test_group(test_session, name="SC4", group_type="family")
    member = await _make_member(test_session, group)

    # AI spike
    for i in range(1, 6):
        await _add_baseline(test_session, member.id, {"ai_session_count": 5.0}, days_ago=i)
    await _add_baseline(test_session, member.id, {"ai_session_count": 50.0}, days_ago=0)

    result = await run_anomaly_scan(test_session, member.id)
    # At least 1 alert should have been created for the AI anomaly
    assert result["alerts_created"] >= 1
