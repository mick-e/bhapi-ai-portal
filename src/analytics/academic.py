"""AI Academic Integrity — intent classification and study-hour analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent
from src.groups.models import GroupMember

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Study-hour defaults
# ---------------------------------------------------------------------------

STUDY_HOUR_DEFAULTS: dict[str, dict[str, str]] = {
    "weekday": {"start": "15:00", "end": "21:00"},
    "weekend": {"start": "09:00", "end": "21:00"},
}

# ---------------------------------------------------------------------------
# Intent classification patterns
# ---------------------------------------------------------------------------

LEARNING_PATTERNS: list[str] = [
    r"\b(explain|how\s+does|what\s+is|why\s+does|teach\s+me|help\s+me\s+understand)\b",
    r"\b(what\s+are\s+the\s+(?:steps|differences|similarities))\b",
    r"\b(can\s+you\s+(?:explain|clarify|break\s+down))\b",
    r"\b(show\s+me\s+(?:how|an?\s+example))\b",
    r"\b(what\s+(?:does|is)\s+\w+\s+mean)\b",
]

DOING_PATTERNS: list[str] = [
    r"\b(write\s+(?:my|an?|the)\s+(?:essay|paper|report|paragraph|summary))\b",
    r"\b(solve\s+(?:this|these|my)\s+(?:problem|equation|homework))\b",
    r"\b(do\s+my\s+(?:homework|assignment|project))\b",
    r"\b(answer\s+(?:these|this|my)\s+(?:question|quiz))\b",
    r"\b(complete\s+(?:this|my)\s+(?:worksheet|assignment))\b",
    r"\b(give\s+me\s+(?:the\s+)?answer)\b",
    r"\b(write\s+(?:a\s+)?(?:\d+[- ]?word|paragraph|page))\b",
]

# Pre-compile patterns for performance
_LEARNING_RE = [re.compile(p, re.IGNORECASE) for p in LEARNING_PATTERNS]
_DOING_RE = [re.compile(p, re.IGNORECASE) for p in DOING_PATTERNS]

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class AcademicReport:
    """Academic usage report for a single member."""

    member_id: UUID
    period_start: date
    period_end: date
    total_ai_sessions: int
    study_hour_sessions: int
    learning_count: int
    doing_count: int
    unclassified_count: int
    learning_ratio: float
    top_subjects: list[str] = field(default_factory=list)
    daily_breakdown: list[dict] = field(default_factory=list)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def classify_prompt_intent(content: str) -> str:
    """Classify prompt text as 'learning', 'doing', or 'unclassified'."""
    if not content or not content.strip():
        return "unclassified"

    text = content.strip()

    # Check "doing" first — it's the riskier category
    for regex in _DOING_RE:
        if regex.search(text):
            return "doing"

    for regex in _LEARNING_RE:
        if regex.search(text):
            return "learning"

    return "unclassified"


async def is_study_hours(
    timestamp: datetime,
    study_config: dict | None = None,
) -> bool:
    """Check if *timestamp* falls within configured study hours.

    Parameters
    ----------
    timestamp:
        A timezone-aware datetime to evaluate.
    study_config:
        Optional dict with ``weekday`` and ``weekend`` keys, each containing
        ``start`` and ``end`` strings in ``HH:MM`` format.  Falls back to
        ``STUDY_HOUR_DEFAULTS`` when *None*.
    """
    config = study_config or STUDY_HOUR_DEFAULTS

    # weekday(): 0=Mon … 6=Sun; Saturday=5, Sunday=6
    is_weekend = timestamp.weekday() >= 5
    day_key = "weekend" if is_weekend else "weekday"
    day_config = config.get(day_key, STUDY_HOUR_DEFAULTS[day_key])

    start_parts = day_config["start"].split(":")
    end_parts = day_config["end"].split(":")

    start_hour, start_min = int(start_parts[0]), int(start_parts[1])
    end_hour, end_min = int(end_parts[0]), int(end_parts[1])

    t = timestamp.hour * 60 + timestamp.minute
    start_t = start_hour * 60 + start_min
    end_t = end_hour * 60 + end_min

    return start_t <= t <= end_t


async def generate_academic_report(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    start_date: date,
    end_date: date,
    study_config: dict | None = None,
) -> AcademicReport:
    """Generate academic usage report for a member over a date range."""

    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    result = await db.execute(
        select(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.member_id == member_id,
            CaptureEvent.timestamp >= start_dt,
            CaptureEvent.timestamp <= end_dt,
        ).order_by(CaptureEvent.timestamp)
    )
    events = list(result.scalars().all())

    learning_count = 0
    doing_count = 0
    unclassified_count = 0
    study_hour_sessions = 0

    # daily buckets
    daily: dict[str, dict[str, int]] = {}

    for event in events:
        content = getattr(event, "content", "") or ""
        intent = await classify_prompt_intent(content)

        if intent == "learning":
            learning_count += 1
        elif intent == "doing":
            doing_count += 1
        else:
            unclassified_count += 1

        if event.timestamp and await is_study_hours(event.timestamp, study_config):
            study_hour_sessions += 1

        day_str = str(event.timestamp.date()) if event.timestamp else "unknown"
        bucket = daily.setdefault(day_str, {"learning": 0, "doing": 0, "unclassified": 0})
        bucket[intent] += 1

    total = learning_count + doing_count + unclassified_count
    classified = learning_count + doing_count
    learning_ratio = (learning_count / classified) if classified > 0 else 0.0

    # Build daily breakdown list
    daily_breakdown = [
        {"date": d, **counts}
        for d, counts in sorted(daily.items())
    ]

    # Generate recommendation
    recommendation = _generate_recommendation(learning_ratio, doing_count, total)

    logger.info(
        "academic_report_generated",
        group_id=str(group_id),
        member_id=str(member_id),
        total=total,
        learning=learning_count,
        doing=doing_count,
    )

    return AcademicReport(
        member_id=member_id,
        period_start=start_date,
        period_end=end_date,
        total_ai_sessions=total,
        study_hour_sessions=study_hour_sessions,
        learning_count=learning_count,
        doing_count=doing_count,
        unclassified_count=unclassified_count,
        learning_ratio=round(learning_ratio, 4),
        top_subjects=[],  # subject extraction is a future enhancement
        daily_breakdown=daily_breakdown,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _generate_recommendation(
    learning_ratio: float,
    doing_count: int,
    total: int,
) -> str:
    """Return a parent-friendly recommendation based on usage patterns."""
    if total == 0:
        return (
            "No AI sessions detected in this period. If your child is using "
            "AI tools, make sure the browser extension is active."
        )

    if learning_ratio >= 0.7:
        return (
            "Great news! Your child is primarily using AI as a learning tool — "
            "asking questions and seeking explanations. Keep encouraging this "
            "healthy pattern."
        )

    if learning_ratio >= 0.4:
        return (
            "Your child has a mix of learning and task-completion requests. "
            "Consider discussing when it is appropriate to ask AI for help "
            "versus doing the work themselves."
        )

    if doing_count > 0:
        return (
            "Your child appears to be asking AI to complete assignments or "
            "produce work for them. We recommend having a conversation about "
            "academic integrity and setting clear expectations for AI use."
        )

    return (
        "Most AI interactions could not be clearly classified. Review the "
        "activity log for more detail."
    )
