"""Safety score calculation service.

Computes composite safety scores for individual members and groups
based on risk event history, weighted by severity and recency.
"""

import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.risk.models import RiskEvent

logger = structlog.get_logger()

# Severity weights: higher weight = more impact on score (lowers safety)
SEVERITY_WEIGHTS = {
    "critical": 40,
    "high": 25,
    "medium": 10,
    "low": 2,
}


class SafetyScore:
    """Composite safety score result for a member."""

    def __init__(
        self,
        score: float,
        trend: str,
        top_categories: list[str],
        risk_count_by_severity: dict[str, int],
        member_id: UUID,
        group_id: UUID,
    ):
        self.score = score
        self.trend = trend
        self.top_categories = top_categories
        self.risk_count_by_severity = risk_count_by_severity
        self.member_id = member_id
        self.group_id = group_id


class GroupScore:
    """Aggregate safety score for a group."""

    def __init__(
        self,
        average_score: float,
        member_scores: list[SafetyScore],
        group_id: UUID,
    ):
        self.average_score = average_score
        self.member_scores = member_scores
        self.group_id = group_id


class ScoreHistoryEntry:
    """A single day's score in the history."""

    def __init__(self, date: str, score: float):
        self.date = date
        self.score = score


def _recency_decay(event_age_days: float) -> float:
    """Apply exponential decay based on event age.

    Recent events have higher impact. Events older than 30 days
    still contribute but with diminishing weight.

    Decay formula: e^(-0.05 * age_days)
    - Day 0: weight 1.0
    - Day 7: weight ~0.70
    - Day 14: weight ~0.50
    - Day 30: weight ~0.22
    """
    return math.exp(-0.05 * event_age_days)


def _ensure_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC).

    SQLite returns naive datetimes; PostgreSQL returns aware ones.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _compute_raw_penalty(events: list[RiskEvent], now: datetime) -> float:
    """Compute the total weighted penalty from risk events."""
    total_penalty = 0.0
    now = _ensure_aware(now)
    for event in events:
        severity_weight = SEVERITY_WEIGHTS.get(event.severity, 2)
        created = _ensure_aware(event.created_at)
        age_days = max(0.0, (now - created).total_seconds() / 86400)
        decay = _recency_decay(age_days)
        total_penalty += severity_weight * decay
    return total_penalty


def _normalize_score(penalty: float) -> float:
    """Normalize raw penalty to a 0-100 score where 100 is safest.

    Uses a sigmoid-like mapping so the score degrades gracefully:
    - 0 penalty -> 100
    - ~50 penalty -> ~73
    - ~100 penalty -> ~50
    - ~200 penalty -> ~18
    """
    # Logistic curve: score = 100 / (1 + penalty/100)
    score = 100.0 / (1.0 + penalty / 100.0)
    return round(max(0.0, min(100.0, score)), 1)


async def calculate_member_score(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    days: int = 30,
) -> SafetyScore:
    """Calculate a composite safety score for a single member.

    Algorithm:
    1. Fetch all risk events for this member in the time window
    2. Weight each event by severity (critical=40, high=25, medium=10, low=2)
    3. Apply recency decay (recent events weigh more)
    4. Normalize to 0-100 scale (100 = safest)
    5. Determine trend by comparing recent vs older halves
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    # Fetch risk events
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id == member_id,
            RiskEvent.created_at >= cutoff,
        ).order_by(RiskEvent.created_at.desc())
    )
    events = list(result.scalars().all())

    # If no events, perfect score
    if not events:
        return SafetyScore(
            score=100.0,
            trend="stable",
            top_categories=[],
            risk_count_by_severity={"critical": 0, "high": 0, "medium": 0, "low": 0},
            member_id=member_id,
            group_id=group_id,
        )

    # Compute penalty and score
    penalty = _compute_raw_penalty(events, now)
    score = _normalize_score(penalty)

    # Count by severity
    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for event in events:
        if event.severity in severity_counts:
            severity_counts[event.severity] += 1

    # Top categories (most frequent first)
    category_counter: Counter[str] = Counter()
    for event in events:
        category_counter[event.category] += 1
    top_categories = [cat for cat, _ in category_counter.most_common(5)]

    # Trend: compare first half vs second half of the period
    midpoint = now - timedelta(days=days / 2)
    recent_events = [e for e in events if _ensure_aware(e.created_at) >= midpoint]
    older_events = [e for e in events if _ensure_aware(e.created_at) < midpoint]

    recent_penalty = _compute_raw_penalty(recent_events, now)
    older_penalty = _compute_raw_penalty(older_events, now)

    if recent_penalty < older_penalty * 0.8:
        trend = "improving"
    elif recent_penalty > older_penalty * 1.2:
        trend = "declining"
    else:
        trend = "stable"

    logger.info(
        "member_safety_score_calculated",
        member_id=str(member_id),
        group_id=str(group_id),
        score=score,
        trend=trend,
        event_count=len(events),
    )

    return SafetyScore(
        score=score,
        trend=trend,
        top_categories=top_categories,
        risk_count_by_severity=severity_counts,
        member_id=member_id,
        group_id=group_id,
    )


async def calculate_group_score(
    db: AsyncSession,
    group_id: UUID,
    days: int = 30,
) -> GroupScore:
    """Calculate aggregate safety score for a group.

    Returns the average score across all members who have risk events,
    along with individual member scores.
    """
    # Find all distinct members with risk events in the period
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    result = await db.execute(
        select(RiskEvent.member_id).where(
            RiskEvent.group_id == group_id,
            RiskEvent.created_at >= cutoff,
        ).distinct()
    )
    member_ids = [row[0] for row in result.all()]

    # If no members have risk events, perfect group score
    if not member_ids:
        return GroupScore(
            average_score=100.0,
            member_scores=[],
            group_id=group_id,
        )

    # Calculate individual scores
    member_scores = []
    for mid in member_ids:
        ms = await calculate_member_score(db, group_id, mid, days)
        member_scores.append(ms)

    # Average
    avg = sum(ms.score for ms in member_scores) / len(member_scores)
    avg = round(avg, 1)

    logger.info(
        "group_safety_score_calculated",
        group_id=str(group_id),
        average_score=avg,
        member_count=len(member_scores),
    )

    return GroupScore(
        average_score=avg,
        member_scores=member_scores,
        group_id=group_id,
    )


async def get_score_history(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    days: int = 30,
) -> list[ScoreHistoryEntry]:
    """Compute daily safety scores over N days for a member.

    Returns a list of (date, score) entries, one per day.
    """
    now = datetime.now(timezone.utc)
    history = []

    # Fetch all events in the extended window (need older events for context)
    extended_cutoff = now - timedelta(days=days * 2)
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id == member_id,
            RiskEvent.created_at >= extended_cutoff,
        ).order_by(RiskEvent.created_at.desc())
    )
    all_events = list(result.scalars().all())

    for day_offset in range(days, -1, -1):
        day_end = now - timedelta(days=day_offset)
        day_cutoff = day_end - timedelta(days=days)

        # Events within the rolling window ending at this day
        window_events = [
            e for e in all_events
            if day_cutoff <= _ensure_aware(e.created_at) <= day_end
        ]

        if not window_events:
            day_score = 100.0
        else:
            penalty = _compute_raw_penalty(window_events, day_end)
            day_score = _normalize_score(penalty)

        history.append(ScoreHistoryEntry(
            date=day_end.strftime("%Y-%m-%d"),
            score=day_score,
        ))

    return history
