"""Behavioral Anomaly Correlation — multi-signal deviation, evasion, cross-signal patterns.

P3-I4: Detects behavioral anomalies for children using BehavioralBaseline records.

Signal types tracked:
  - ai_usage        — AI session count / duration from BehavioralBaseline metrics
  - screen_time     — Total daily screen minutes from ScreenTimeRecord
  - social_activity — Social post / message counts from BehavioralBaseline metrics
  - location_movement — Placeholder (location module added in Phase 3)

All public functions return plain dicts for cross-module safety.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.device_agent.models import ScreenTimeRecord
from src.groups.models import GroupMember
from src.intelligence.correlation import create_enriched_alert
from src.intelligence.models import BehavioralBaseline

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASELINE_WINDOW_DAYS = 30          # Look back 30 days for baseline records
_ANOMALY_THRESHOLD_SIGMA = 2.0      # Flag if |current - mean| > 2σ
_EVASION_DROP_THRESHOLD = 0.50      # AI usage must drop >50% below baseline
_EVASION_SCREEN_STABLE = 0.20       # Screen time must stay within ±20% of baseline

# Signal type labels
SIGNAL_AI_USAGE = "ai_usage"
SIGNAL_SCREEN_TIME = "screen_time"
SIGNAL_SOCIAL_ACTIVITY = "social_activity"
SIGNAL_LOCATION = "location_movement"

_ALL_SIGNALS = (
    SIGNAL_AI_USAGE,
    SIGNAL_SCREEN_TIME,
    SIGNAL_SOCIAL_ACTIVITY,
    SIGNAL_LOCATION,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _safe_mean(values: list[float]) -> float:
    """Return arithmetic mean, 0.0 for empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _safe_std(values: list[float]) -> float:
    """Return population standard deviation, 0.0 for empty or single-element list."""
    if len(values) < 2:
        return 0.0
    mean = _safe_mean(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _deviation_factor(current: float, mean: float, std: float) -> float:
    """Return signed standard-deviation count.

    Positive = above mean, negative = below mean.
    Returns ±99.0 (capped) when std=0 and current != mean, to avoid JSON ±inf.
    Returns 0.0 when std=0 and current == mean.
    """
    if std == 0.0:
        if current == mean:
            return 0.0
        # Cap at ±99 instead of ±inf to stay JSON-serializable
        return math.copysign(99.0, current - mean)
    return (current - mean) / std


# ---------------------------------------------------------------------------
# Signal extraction helpers — read from BehavioralBaseline metrics
# ---------------------------------------------------------------------------


def _extract_ai_usage(metrics: dict) -> float | None:
    """Return AI session count/proxy from baseline metrics dict.

    Accepts several key names produced by different baseline computations.
    """
    for key in ("ai_session_count", "ai_sessions", "ai_usage", "session_count"):
        val = metrics.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def _extract_social_activity(metrics: dict) -> float | None:
    """Return social activity proxy (posts + messages per day)."""
    posts = metrics.get("avg_posts_per_day")
    msgs = metrics.get("avg_messages_per_day")

    if posts is None and msgs is None:
        for key in ("social_activity", "social_count", "social_posts"):
            val = metrics.get(key)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    continue
        return None

    total = 0.0
    if posts is not None:
        try:
            # avg_posts_per_day may be a dict {mean, std} or a scalar
            if isinstance(posts, dict):
                total += float(posts.get("mean", 0.0))
            else:
                total += float(posts)
        except (TypeError, ValueError):
            pass
    if msgs is not None:
        try:
            if isinstance(msgs, dict):
                total += float(msgs.get("mean", 0.0))
            else:
                total += float(msgs)
        except (TypeError, ValueError):
            pass
    return total


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def _get_recent_baselines(
    db: AsyncSession,
    child_id: UUID,
    window_days: int = _BASELINE_WINDOW_DAYS,
) -> list[BehavioralBaseline]:
    """Return BehavioralBaseline rows for this child within window_days, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    result = await db.execute(
        select(BehavioralBaseline)
        .where(
            BehavioralBaseline.member_id == child_id,
            BehavioralBaseline.computed_at >= cutoff,
        )
        .order_by(BehavioralBaseline.computed_at.desc())
    )
    return list(result.scalars().all())


async def _get_recent_screen_time(
    db: AsyncSession,
    child_id: UUID,
    days: int = _BASELINE_WINDOW_DAYS,
) -> list[float]:
    """Return daily total_minutes from ScreenTimeRecord for the last N days.

    Ordered newest-first so index 0 is the most recent day.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    result = await db.execute(
        select(ScreenTimeRecord.total_minutes)
        .where(
            ScreenTimeRecord.member_id == child_id,
            ScreenTimeRecord.date >= cutoff,
        )
        .order_by(ScreenTimeRecord.date.desc())
    )
    return [float(v) for v in result.scalars().all()]


async def _get_group_id(db: AsyncSession, child_id: UUID) -> UUID | None:
    """Return the group_id for a group member."""
    result = await db.execute(
        select(GroupMember.group_id).where(GroupMember.id == child_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 1. Multi-signal deviation
# ---------------------------------------------------------------------------


async def compute_multi_signal_deviation(
    db: AsyncSession,
    child_id: UUID,
) -> list[dict]:
    """Compute per-signal deviations against baseline statistics.

    Reads BehavioralBaseline records from the last 30 days.
    Computes mean + stddev per signal across all baseline snapshots.
    Flags deviations >2σ from the mean.

    Returns:
        List of dicts:
        {
            "signal_type":      str,
            "current_value":    float,
            "mean":             float,
            "stddev":           float,
            "deviation_factor": float,     # signed standard deviations
            "is_anomalous":     bool,
        }
    """
    baselines = await _get_recent_baselines(db, child_id)
    screen_times = await _get_recent_screen_time(db, child_id)

    results: list[dict] = []

    # --- AI usage signal ---
    # Requires at least 2 data points: one for current, one+ for baseline stats.
    ai_values: list[float] = []
    for b in baselines:
        if not b.metrics:
            continue
        val = _extract_ai_usage(b.metrics)
        if val is not None:
            ai_values.append(val)

    if len(ai_values) >= 2:
        current = ai_values[0]   # most recent baseline
        baseline_vals = ai_values[1:]
        mean = _safe_mean(baseline_vals)
        std = _safe_std(baseline_vals)
        dev = _deviation_factor(current, mean, std)
        results.append({
            "signal_type": SIGNAL_AI_USAGE,
            "current_value": current,
            "mean": mean,
            "stddev": std,
            "deviation_factor": dev,
            "is_anomalous": abs(dev) > _ANOMALY_THRESHOLD_SIGMA,
        })

    # --- Screen time signal ---
    # Requires at least 2 data points (today + at least 1 historical day).
    if len(screen_times) >= 2:
        current_screen = screen_times[0]
        baseline_screen = screen_times[1:]
        mean = _safe_mean(baseline_screen)
        std = _safe_std(baseline_screen)
        dev = _deviation_factor(current_screen, mean, std)
        results.append({
            "signal_type": SIGNAL_SCREEN_TIME,
            "current_value": current_screen,
            "mean": mean,
            "stddev": std,
            "deviation_factor": dev,
            "is_anomalous": abs(dev) > _ANOMALY_THRESHOLD_SIGMA,
        })

    # --- Social activity signal ---
    # Requires at least 2 data points.
    social_values: list[float] = []
    for b in baselines:
        if not b.metrics:
            continue
        val = _extract_social_activity(b.metrics)
        if val is not None:
            social_values.append(val)

    if len(social_values) >= 2:
        current = social_values[0]
        baseline_vals = social_values[1:]
        mean = _safe_mean(baseline_vals)
        std = _safe_std(baseline_vals)
        dev = _deviation_factor(current, mean, std)
        results.append({
            "signal_type": SIGNAL_SOCIAL_ACTIVITY,
            "current_value": current,
            "mean": mean,
            "stddev": std,
            "deviation_factor": dev,
            "is_anomalous": abs(dev) > _ANOMALY_THRESHOLD_SIGMA,
        })

    # --- Location movement signal (placeholder) ---
    results.append({
        "signal_type": SIGNAL_LOCATION,
        "current_value": 0.0,
        "mean": 0.0,
        "stddev": 0.0,
        "deviation_factor": 0.0,
        "is_anomalous": False,
    })

    logger.info(
        "multi_signal_deviation_computed",
        child_id=str(child_id),
        signal_count=len(results),
        anomalous_count=sum(1 for r in results if r["is_anomalous"]),
    )
    return results


# ---------------------------------------------------------------------------
# 2. Evasion detection
# ---------------------------------------------------------------------------


async def detect_evasion(
    db: AsyncSession,
    child_id: UUID,
) -> dict | None:
    """Detect possible platform-switching evasion.

    Pattern: AI usage drops >50% below baseline while screen time stays
    stable or increases (within ±20% of baseline).  This suggests the
    child moved to an unmonitored platform rather than genuinely reducing
    screen time.

    Returns:
        EvasionResult dict if detected, None otherwise:
        {
            "child_id":          str (UUID),
            "ai_usage_current":  float,
            "ai_usage_baseline": float,
            "ai_drop_pct":       float,    # 0-1, positive = drop
            "screen_time_current":  float,
            "screen_time_baseline": float,
            "screen_change_pct":    float, # signed, negative = drop
            "confidence":        str,      # "low" | "medium" | "high"
            "reason":            str,
        }
    """
    baselines = await _get_recent_baselines(db, child_id)
    screen_times = await _get_recent_screen_time(db, child_id)

    # Need at least 2 baseline snapshots for AI usage history
    ai_values: list[float] = []
    for b in baselines:
        if b.metrics:
            val = _extract_ai_usage(b.metrics)
            if val is not None:
                ai_values.append(val)

    if len(ai_values) < 2:
        return None

    current_ai = ai_values[0]
    baseline_ai = _safe_mean(ai_values[1:])

    if baseline_ai == 0.0:
        # Cannot compute relative drop from zero baseline
        return None

    ai_drop_pct = (baseline_ai - current_ai) / baseline_ai  # positive = usage dropped

    if ai_drop_pct <= _EVASION_DROP_THRESHOLD:
        # AI usage did not drop enough to trigger evasion suspicion
        return None

    # Check screen time — if screen time also dropped significantly,
    # this is likely a genuine reduction, NOT evasion
    if len(screen_times) < 2:
        # No screen time data — cannot confirm evasion
        return None

    current_screen = screen_times[0]
    baseline_screen = _safe_mean(screen_times[1:])

    screen_change_pct = (
        (current_screen - baseline_screen) / baseline_screen
        if baseline_screen != 0.0
        else 0.0
    )

    # Evasion requires screen time to remain stable (≥ -20% change)
    # i.e., screen time did NOT drop significantly
    if screen_change_pct < -_EVASION_SCREEN_STABLE:
        # Screen time also dropped — legitimate reduction, not evasion
        return None

    # Confidence: higher AI drop + more baseline snapshots = higher confidence
    if ai_drop_pct >= 0.75 and len(ai_values) >= 5:
        confidence = "high"
    elif ai_drop_pct >= 0.60:
        confidence = "medium"
    else:
        confidence = "low"

    reason = (
        f"AI usage dropped {ai_drop_pct:.0%} below baseline while screen time "
        f"remained {'stable' if abs(screen_change_pct) <= 0.05 else 'increased'} "
        f"({screen_change_pct:+.0%})."
    )

    logger.info(
        "evasion_detected",
        child_id=str(child_id),
        ai_drop_pct=round(ai_drop_pct, 3),
        screen_change_pct=round(screen_change_pct, 3),
        confidence=confidence,
    )

    return {
        "child_id": str(child_id),
        "ai_usage_current": current_ai,
        "ai_usage_baseline": baseline_ai,
        "ai_drop_pct": round(ai_drop_pct, 4),
        "screen_time_current": current_screen,
        "screen_time_baseline": baseline_screen,
        "screen_change_pct": round(screen_change_pct, 4),
        "confidence": confidence,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# 3. Cross-signal anomaly detection
# ---------------------------------------------------------------------------


async def detect_cross_signal_anomalies(
    db: AsyncSession,
    child_id: UUID,
) -> list[dict]:
    """Detect combined cross-signal patterns that individually may be benign.

    Patterns checked:
    1. Social withdrawal + AI usage spike
       (reduced social_activity AND increased ai_usage in same window)
    2. Location change + new contacts
       (new geofence visits AND contact requests in same timeframe)
       — placeholder: location signals not yet available

    Returns:
        List of CrossSignalAnomaly dicts:
        {
            "pattern_type": str,
            "signals":      list[str],
            "description":  str,
            "severity":     str,   # "low" | "medium" | "high"
            "details":      dict,
        }
    """
    baselines = await _get_recent_baselines(db, child_id)
    anomalies: list[dict] = []

    if len(baselines) < 2:
        return anomalies

    # Extract current + baseline for AI and social signals
    ai_values: list[float] = []
    social_values: list[float] = []

    for b in baselines:
        if not b.metrics:
            continue
        ai_val = _extract_ai_usage(b.metrics)
        if ai_val is not None:
            ai_values.append(ai_val)
        social_val = _extract_social_activity(b.metrics)
        if social_val is not None:
            social_values.append(social_val)

    # Pattern 1: Social withdrawal + AI spike
    if len(ai_values) >= 2 and len(social_values) >= 2:
        current_ai = ai_values[0]
        baseline_ai = _safe_mean(ai_values[1:])
        current_social = social_values[0]
        baseline_social = _safe_mean(social_values[1:])

        std_ai = _safe_std(ai_values[1:])
        std_social = _safe_std(social_values[1:])

        ai_dev = _deviation_factor(current_ai, baseline_ai, std_ai)
        social_dev = _deviation_factor(current_social, baseline_social, std_social)

        # AI spiked (>1.5σ above) AND social dropped (>1.5σ below).
        # When std=0 (perfect baseline uniformity), require a ≥50% absolute change
        # rather than infinite σ, to avoid noise from tiny numeric differences.
        if std_ai > 0:
            ai_spiked = ai_dev > 1.5
        else:
            ai_spiked = baseline_ai > 0 and (current_ai / baseline_ai) >= 1.5

        if std_social > 0:
            social_dropped = social_dev < -1.5
        else:
            social_dropped = baseline_social > 0 and (current_social / baseline_social) <= 0.5

        if ai_spiked and social_dropped:
            severity = "high" if ai_dev > 2.5 and social_dev < -2.5 else "medium"
            anomalies.append({
                "pattern_type": "social_withdrawal_ai_spike",
                "signals": [SIGNAL_AI_USAGE, SIGNAL_SOCIAL_ACTIVITY],
                "description": (
                    "Reduced social activity combined with increased AI usage "
                    "may indicate the child is substituting peer interaction with AI."
                ),
                "severity": severity,
                "details": {
                    "ai_deviation_sigma": round(ai_dev, 3),
                    "social_deviation_sigma": round(social_dev, 3),
                    "current_ai_usage": current_ai,
                    "baseline_ai_usage": round(baseline_ai, 3),
                    "current_social_activity": current_social,
                    "baseline_social_activity": round(baseline_social, 3),
                },
            })

    # Pattern 2: Location change + new contacts (placeholder — location not yet tracked)
    # This will be enriched when the location module delivers data (Phase 3).

    if anomalies:
        logger.info(
            "cross_signal_anomalies_detected",
            child_id=str(child_id),
            count=len(anomalies),
            patterns=[a["pattern_type"] for a in anomalies],
        )

    return anomalies


# ---------------------------------------------------------------------------
# 4. Full scan
# ---------------------------------------------------------------------------


async def run_anomaly_scan(
    db: AsyncSession,
    child_id: UUID,
) -> dict:
    """Run all anomaly detectors and create EnrichedAlert entries for findings.

    Runs:
    - compute_multi_signal_deviation
    - detect_evasion
    - detect_cross_signal_anomalies

    For anomalies found, creates Alert + EnrichedAlert DB rows so parents
    are notified via the existing alerts pipeline.

    Returns:
        {
            "child_id":                 str,
            "scanned_at":               str (ISO 8601),
            "signal_anomalies":         list[dict],
            "evasion":                  dict | None,
            "cross_signal_anomalies":   list[dict],
            "total_anomalies":          int,
            "alerts_created":           int,
        }
    """
    scanned_at = datetime.now(timezone.utc)

    signal_anomalies = await compute_multi_signal_deviation(db, child_id)
    evasion = await detect_evasion(db, child_id)
    cross_signal = await detect_cross_signal_anomalies(db, child_id)

    alerts_created = 0
    group_id = await _get_group_id(db, child_id)

    if group_id is not None:
        # Create alerts for flagged signal deviations
        for sig in signal_anomalies:
            if not sig["is_anomalous"]:
                continue
            try:
                alert = Alert(
                    id=uuid4(),
                    group_id=group_id,
                    member_id=child_id,
                    source="ai",
                    severity="medium",
                    title=f"Behavioral anomaly: {sig['signal_type']}",
                    body=(
                        f"{sig['signal_type']} is {abs(sig['deviation_factor']):.1f}σ "
                        f"from baseline (current={sig['current_value']:.1f}, "
                        f"mean={sig['mean']:.1f})."
                    ),
                    channel="portal",
                    status="pending",
                )
                db.add(alert)
                await db.flush()

                await create_enriched_alert(
                    db=db,
                    alert_id=alert.id,
                    rule_id=None,
                    context=f"Anomaly detected for signal: {sig['signal_type']}",
                    signals={
                        "signal_type": sig["signal_type"],
                        "deviation_factor": sig["deviation_factor"],
                        "current_value": sig["current_value"],
                        "mean": sig["mean"],
                        "stddev": sig["stddev"],
                    },
                    score=min(100.0, abs(sig["deviation_factor"]) * 25.0),
                    confidence="medium",
                )
                alerts_created += 1
            except Exception:
                logger.exception(
                    "anomaly_alert_creation_failed",
                    child_id=str(child_id),
                    signal_type=sig["signal_type"],
                )

        # Create alert for evasion
        if evasion is not None:
            try:
                alert = Alert(
                    id=uuid4(),
                    group_id=group_id,
                    member_id=child_id,
                    source="ai",
                    severity="high",
                    title="Possible platform evasion detected",
                    body=evasion["reason"],
                    channel="portal",
                    status="pending",
                )
                db.add(alert)
                await db.flush()

                await create_enriched_alert(
                    db=db,
                    alert_id=alert.id,
                    rule_id=None,
                    context="Evasion pattern: AI usage drop with stable screen time",
                    signals={
                        "ai_drop_pct": evasion["ai_drop_pct"],
                        "screen_change_pct": evasion["screen_change_pct"],
                        "ai_usage_current": evasion["ai_usage_current"],
                        "ai_usage_baseline": evasion["ai_usage_baseline"],
                    },
                    score=min(100.0, evasion["ai_drop_pct"] * 100.0),
                    confidence=evasion["confidence"],
                )
                alerts_created += 1
            except Exception:
                logger.exception(
                    "evasion_alert_creation_failed",
                    child_id=str(child_id),
                )

        # Create alert for cross-signal anomalies
        for cs in cross_signal:
            try:
                sev_map = {"high": "high", "medium": "medium", "low": "low"}
                alert = Alert(
                    id=uuid4(),
                    group_id=group_id,
                    member_id=child_id,
                    source="ai",
                    severity=sev_map.get(cs["severity"], "medium"),
                    title=f"Cross-signal pattern: {cs['pattern_type']}",
                    body=cs["description"],
                    channel="portal",
                    status="pending",
                )
                db.add(alert)
                await db.flush()

                await create_enriched_alert(
                    db=db,
                    alert_id=alert.id,
                    rule_id=None,
                    context=f"Cross-signal anomaly pattern: {cs['pattern_type']}",
                    signals=cs["details"],
                    score=75.0 if cs["severity"] == "high" else 50.0,
                    confidence="medium",
                )
                alerts_created += 1
            except Exception:
                logger.exception(
                    "cross_signal_alert_creation_failed",
                    child_id=str(child_id),
                    pattern_type=cs["pattern_type"],
                )

    total_anomalies = (
        sum(1 for s in signal_anomalies if s["is_anomalous"])
        + (1 if evasion else 0)
        + len(cross_signal)
    )

    logger.info(
        "anomaly_scan_complete",
        child_id=str(child_id),
        total_anomalies=total_anomalies,
        alerts_created=alerts_created,
    )

    return {
        "child_id": str(child_id),
        "scanned_at": scanned_at.isoformat(),
        "signal_anomalies": signal_anomalies,
        "evasion": evasion,
        "cross_signal_anomalies": cross_signal,
        "total_anomalies": total_anomalies,
        "alerts_created": alerts_created,
    }
