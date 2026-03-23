"""Unified risk scoring — weighted 4-source score, confidence, trends.

Computes a 0-100 unified risk score from four signal sources:
  - AI monitoring   (RiskEvent table)
  - Social behavior (BehavioralBaseline metrics)
  - Device usage    (ScreenTimeRecord daily minutes)
  - Location        (placeholder — returns 0 until Task 7)

Final score = weighted sum per age tier (YOUNG / PRETEEN / TEEN).
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import AgeTier, age_from_dob, get_tier_for_age
from src.device_agent.models import ScreenTimeRecord
from src.groups.models import GroupMember
from src.intelligence.models import BehavioralBaseline
from src.risk.models import RiskEvent

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Weight tables per age tier
# ---------------------------------------------------------------------------

# Keys: (tier, source) → weight
_WEIGHTS: dict[tuple[AgeTier, str], float] = {
    # Young (5-9)
    (AgeTier.YOUNG, "ai_monitoring"):    0.40,
    (AgeTier.YOUNG, "social_behavior"):  0.20,
    (AgeTier.YOUNG, "device_usage"):     0.20,
    (AgeTier.YOUNG, "location"):         0.20,
    # Preteen (10-12)
    (AgeTier.PRETEEN, "ai_monitoring"):   0.30,
    (AgeTier.PRETEEN, "social_behavior"): 0.30,
    (AgeTier.PRETEEN, "device_usage"):    0.20,
    (AgeTier.PRETEEN, "location"):        0.20,
    # Teen (13-15)
    (AgeTier.TEEN, "ai_monitoring"):   0.25,
    (AgeTier.TEEN, "social_behavior"): 0.35,
    (AgeTier.TEEN, "device_usage"):    0.20,
    (AgeTier.TEEN, "location"):        0.20,
}

# Severity → penalty points (same mapping as src/risk/score.py)
_SEVERITY_PENALTY = {
    "critical": 40,
    "high":     25,
    "medium":   10,
    "low":       2,
}

# Baseline screen-time thresholds (minutes per day) for scoring
_SCREEN_TIME_MAX_MINUTES = 480.0   # 8 hours = max risk (score 100)
_SCREEN_TIME_WARN_MINUTES = 120.0  # 2 hours = low risk (score 0)

SOURCES = ("ai_monitoring", "social_behavior", "device_usage", "location")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_tier() -> AgeTier:
    """Fallback tier when child has no DOB — treat as preteen."""
    return AgeTier.PRETEEN


async def _get_member_tier(db: AsyncSession, child_id: UUID) -> AgeTier:
    """Return the age tier for a group member, defaulting to PRETEEN."""
    result = await db.execute(
        select(GroupMember.date_of_birth).where(GroupMember.id == child_id)
    )
    dob = result.scalar_one_or_none()
    if dob is None:
        return _default_tier()
    age = age_from_dob(dob)
    tier = get_tier_for_age(age)
    return tier if tier is not None else _default_tier()


async def _compute_ai_monitoring_score(db: AsyncSession, child_id: UUID) -> float:
    """Return 0-100 sub-score from RiskEvent severity history (last 30 days).

    Score = clamp(penalty_sum / 100 * 100, 0, 100).
    Penalty accumulates per event weighted by severity.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(RiskEvent.severity).where(
            RiskEvent.member_id == child_id,
            RiskEvent.created_at >= cutoff,
        )
    )
    severities = result.scalars().all()
    if not severities:
        return 0.0

    total_penalty = sum(_SEVERITY_PENALTY.get(s, 0) for s in severities)
    # Normalize: 100 points of penalty → score 100
    score = min(100.0, total_penalty)
    return round(score, 2)


async def _compute_social_behavior_score(db: AsyncSession, child_id: UUID) -> float:
    """Return 0-100 sub-score from BehavioralBaseline metrics.

    Uses the most-recent baseline record. Looks for a 'risk_score' key in
    metrics; falls back to 0 (safe) when no baseline exists.
    """
    result = await db.execute(
        select(BehavioralBaseline.metrics, BehavioralBaseline.computed_at)
        .where(BehavioralBaseline.member_id == child_id)
        .order_by(BehavioralBaseline.computed_at.desc())
        .limit(1)
    )
    row = result.first()
    if row is None or row.metrics is None:
        return 0.0

    metrics = row.metrics
    # Accept several possible metric keys
    for key in ("risk_score", "anomaly_score", "baseline_risk"):
        value = metrics.get(key)
        if value is not None:
            try:
                return float(min(100.0, max(0.0, float(value))))
            except (TypeError, ValueError):
                pass
    return 0.0


async def _compute_device_usage_score(db: AsyncSession, child_id: UUID) -> float:
    """Return 0-100 sub-score from ScreenTimeRecord (last 7 days average).

    Score linearly scales:
      ≤ 2 h/day  → 0
      ≥ 8 h/day  → 100
    """
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=7)
    result = await db.execute(
        select(ScreenTimeRecord.total_minutes).where(
            ScreenTimeRecord.member_id == child_id,
            ScreenTimeRecord.date >= cutoff,
        )
    )
    records = result.scalars().all()
    if not records:
        return 0.0

    avg_minutes = sum(records) / len(records)
    if avg_minutes <= _SCREEN_TIME_WARN_MINUTES:
        return 0.0
    if avg_minutes >= _SCREEN_TIME_MAX_MINUTES:
        return 100.0
    ratio = (avg_minutes - _SCREEN_TIME_WARN_MINUTES) / (
        _SCREEN_TIME_MAX_MINUTES - _SCREEN_TIME_WARN_MINUTES
    )
    return round(ratio * 100.0, 2)


def _compute_location_score() -> float:
    """Placeholder — returns 0 until the location module exists (Task 7)."""
    return 0.0


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------


async def _compute_confidence(db: AsyncSession, child_id: UUID) -> str:
    """Determine confidence level based on earliest data point.

    < 7 days of data  → "low"
    7-30 days         → "medium"
    30+ days          → "high"
    """
    now = datetime.now(timezone.utc)

    # Find the earliest timestamp across all sources
    earliest: datetime | None = None

    # RiskEvent
    res = await db.execute(
        select(func.min(RiskEvent.created_at)).where(
            RiskEvent.member_id == child_id
        )
    )
    risk_min = res.scalar_one_or_none()
    if risk_min is not None:
        risk_min = risk_min.replace(tzinfo=timezone.utc) if risk_min.tzinfo is None else risk_min
        if earliest is None or risk_min < earliest:
            earliest = risk_min

    # BehavioralBaseline
    res = await db.execute(
        select(func.min(BehavioralBaseline.computed_at)).where(
            BehavioralBaseline.member_id == child_id
        )
    )
    baseline_min = res.scalar_one_or_none()
    if baseline_min is not None:
        baseline_min = baseline_min.replace(tzinfo=timezone.utc) if baseline_min.tzinfo is None else baseline_min
        if earliest is None or baseline_min < earliest:
            earliest = baseline_min

    # ScreenTimeRecord (Date column — convert to datetime)
    res = await db.execute(
        select(func.min(ScreenTimeRecord.date)).where(
            ScreenTimeRecord.member_id == child_id
        )
    )
    screen_min = res.scalar_one_or_none()
    if screen_min is not None:
        if isinstance(screen_min, str):
            screen_min = date.fromisoformat(screen_min)
        screen_min_dt = datetime(
            screen_min.year, screen_min.month, screen_min.day, tzinfo=timezone.utc
        )
        if earliest is None or screen_min_dt < earliest:
            earliest = screen_min_dt

    if earliest is None:
        return "low"

    days_of_data = (now - earliest).days
    if days_of_data < 7:
        return "low"
    if days_of_data < 30:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_unified_score(
    db: AsyncSession,
    child_id: UUID,
) -> dict:
    """Compute a 0-100 unified risk score for a child.

    Returns:
        {
            "child_id": UUID,
            "unified_score": float,
            "confidence": str,
            "trend": str,
            "age_tier": str,
        }
    """
    tier = await _get_member_tier(db, child_id)

    sub_scores = {
        "ai_monitoring":   await _compute_ai_monitoring_score(db, child_id),
        "social_behavior": await _compute_social_behavior_score(db, child_id),
        "device_usage":    await _compute_device_usage_score(db, child_id),
        "location":        _compute_location_score(),
    }

    unified = sum(
        sub_scores[source] * _WEIGHTS[(tier, source)]
        for source in SOURCES
    )
    unified = round(min(100.0, max(0.0, unified)), 2)

    confidence = await _compute_confidence(db, child_id)
    trend = await get_score_trend(db, child_id)

    logger.info(
        "unified_score_computed",
        child_id=str(child_id),
        unified_score=unified,
        age_tier=tier.value,
        confidence=confidence,
    )

    return {
        "child_id": child_id,
        "unified_score": unified,
        "confidence": confidence,
        "trend": trend,
        "age_tier": tier.value,
    }


async def get_score_trend(
    db: AsyncSession,
    child_id: UUID,
    days: int = 30,
) -> str:
    """Return rolling trend: 'increasing' / 'stable' / 'decreasing'.

    Compares current AI monitoring score to the score from `days` ago.
    "stable" when |difference| < 5 points.
    """
    now = datetime.now(timezone.utc)
    current_cutoff = now - timedelta(days=7)
    past_cutoff = now - timedelta(days=days + 7)
    past_end = now - timedelta(days=days)

    # Current window (last 7 days)
    res = await db.execute(
        select(RiskEvent.severity).where(
            RiskEvent.member_id == child_id,
            RiskEvent.created_at >= current_cutoff,
        )
    )
    current_severities = res.scalars().all()
    current = min(100.0, sum(_SEVERITY_PENALTY.get(s, 0) for s in current_severities))

    # Past window (7 days around `days` ago)
    res = await db.execute(
        select(RiskEvent.severity).where(
            RiskEvent.member_id == child_id,
            RiskEvent.created_at >= past_cutoff,
            RiskEvent.created_at < past_end,
        )
    )
    past_severities = res.scalars().all()
    past = min(100.0, sum(_SEVERITY_PENALTY.get(s, 0) for s in past_severities))

    diff = current - past
    if abs(diff) < 5.0:
        return "stable"
    return "increasing" if diff > 0 else "decreasing"


async def get_score_breakdown(
    db: AsyncSession,
    child_id: UUID,
) -> dict:
    """Return per-signal-source breakdown.

    Returns:
        {
            "child_id": UUID,
            "sources": [
                {
                    "source": str,
                    "sub_score": float,
                    "weight": float,
                    "weighted_contribution": float,
                },
                ...
            ],
            "unified_score": float,
        }
    """
    tier = await _get_member_tier(db, child_id)

    sub_scores = {
        "ai_monitoring":   await _compute_ai_monitoring_score(db, child_id),
        "social_behavior": await _compute_social_behavior_score(db, child_id),
        "device_usage":    await _compute_device_usage_score(db, child_id),
        "location":        _compute_location_score(),
    }

    sources = []
    unified = 0.0
    for source in SOURCES:
        weight = _WEIGHTS[(tier, source)]
        contribution = round(sub_scores[source] * weight, 4)
        unified += contribution
        sources.append(
            {
                "source": source,
                "sub_score": sub_scores[source],
                "weight": weight,
                "weighted_contribution": contribution,
            }
        )

    unified = round(min(100.0, max(0.0, unified)), 2)

    return {
        "child_id": child_id,
        "sources": sources,
        "unified_score": unified,
    }


async def get_score_history(
    db: AsyncSession,
    child_id: UUID,
    days: int = 30,
) -> dict:
    """Return daily score history for the last N days.

    Builds a per-day risk score from RiskEvent records.
    Days with no events receive score 0.

    Returns:
        {
            "child_id": UUID,
            "history": [{"date": "YYYY-MM-DD", "score": float}, ...],
        }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    res = await db.execute(
        select(RiskEvent.severity, RiskEvent.created_at).where(
            RiskEvent.member_id == child_id,
            RiskEvent.created_at >= cutoff,
        ).order_by(RiskEvent.created_at)
    )
    rows = res.all()

    # Accumulate penalties per calendar day
    daily: dict[str, float] = {}
    for row in rows:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        day_str = created_at.date().isoformat()
        penalty = _SEVERITY_PENALTY.get(row.severity, 0)
        daily[day_str] = min(100.0, daily.get(day_str, 0.0) + penalty)

    # Build ordered list for the requested date range
    history = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date()
        day_str = d.isoformat()
        history.append(
            {
                "date": day_str,
                "score": round(daily.get(day_str, 0.0), 2),
            }
        )

    return {
        "child_id": child_id,
        "history": history,
    }
