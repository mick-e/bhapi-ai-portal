"""Time budget management for AI screen time limits."""

import uuid
from datetime import date, datetime, timedelta, timezone

import structlog
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.blocking.models import BlockRule
from src.database import Base
from src.exceptions import ValidationError
from src.models import TimestampMixin, UUIDMixin

logger = structlog.get_logger()


# ─── Models ─────────────────────────────────────────────────────────────────


class TimeBudget(Base, UUIDMixin, TimestampMixin):
    """Daily AI screen time budget configuration for a member."""

    __tablename__ = "time_budgets"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    weekday_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    weekend_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    reset_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    warn_at_percent: Mapped[int] = mapped_column(Integer, default=75, nullable=False)


class TimeBudgetUsage(Base, UUIDMixin, TimestampMixin):
    """Daily usage tracking against a member's time budget."""

    __tablename__ = "time_budget_usage"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    minutes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    exceeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exceeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ─── Service Functions ───────────────────────────────────────────────────────


def _is_weekend(d: date) -> bool:
    """Check if a date is Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5


def _get_today_for_tz(tz_name: str) -> date:
    """Get current date in the specified timezone."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        now = datetime.now(timezone.utc)
    return now.date()


async def check_time_budget(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> dict:
    """Check a member's current time budget status for today.

    Returns: {minutes_used, budget_minutes, remaining, exceeded, warn}
    """
    # Get budget config
    result = await db.execute(
        select(TimeBudget).where(
            TimeBudget.group_id == group_id,
            TimeBudget.member_id == member_id,
            TimeBudget.enabled.is_(True),
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        return {
            "minutes_used": 0,
            "budget_minutes": 0,
            "remaining": 0,
            "exceeded": False,
            "warn": False,
            "enabled": False,
        }

    today = _get_today_for_tz(budget.timezone)
    budget_minutes = budget.weekend_minutes if _is_weekend(today) else budget.weekday_minutes

    # Get today's usage
    usage_result = await db.execute(
        select(TimeBudgetUsage).where(
            TimeBudgetUsage.group_id == group_id,
            TimeBudgetUsage.member_id == member_id,
            TimeBudgetUsage.date == today,
        )
    )
    usage = usage_result.scalar_one_or_none()

    minutes_used = usage.minutes_used if usage else 0
    remaining = max(0, budget_minutes - minutes_used)
    exceeded = minutes_used >= budget_minutes
    warn_threshold = budget_minutes * budget.warn_at_percent / 100
    warn = minutes_used >= warn_threshold and not exceeded

    return {
        "minutes_used": minutes_used,
        "budget_minutes": budget_minutes,
        "remaining": remaining,
        "exceeded": exceeded,
        "warn": warn,
        "enabled": True,
    }


async def record_session_time(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    minutes: int,
) -> TimeBudgetUsage:
    """Add minutes to a member's daily usage.

    Creates the usage record if it doesn't exist for today.
    """
    if minutes <= 0:
        raise ValidationError("Minutes must be positive")

    # Get budget config for timezone and budget_minutes
    budget_result = await db.execute(
        select(TimeBudget).where(
            TimeBudget.group_id == group_id,
            TimeBudget.member_id == member_id,
        )
    )
    budget = budget_result.scalar_one_or_none()
    tz_name = budget.timezone if budget else "UTC"
    today = _get_today_for_tz(tz_name)

    if budget:
        budget_minutes = budget.weekend_minutes if _is_weekend(today) else budget.weekday_minutes
    else:
        budget_minutes = 0

    # Upsert usage record
    usage_result = await db.execute(
        select(TimeBudgetUsage).where(
            TimeBudgetUsage.group_id == group_id,
            TimeBudgetUsage.member_id == member_id,
            TimeBudgetUsage.date == today,
        )
    )
    usage = usage_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if usage:
        usage.minutes_used += minutes
        if usage.minutes_used >= budget_minutes and budget_minutes > 0 and not usage.exceeded:
            usage.exceeded = True
            usage.exceeded_at = now
    else:
        exceeded = minutes >= budget_minutes and budget_minutes > 0
        usage = TimeBudgetUsage(
            id=uuid.uuid4(),
            group_id=group_id,
            member_id=member_id,
            date=today,
            minutes_used=minutes,
            budget_minutes=budget_minutes,
            exceeded=exceeded,
            exceeded_at=now if exceeded else None,
        )
        db.add(usage)

    await db.flush()
    await db.refresh(usage)

    logger.info(
        "session_time_recorded",
        member_id=str(member_id),
        minutes=minutes,
        total_today=usage.minutes_used,
    )
    return usage


async def enforce_time_budgets(db: AsyncSession) -> dict:
    """Job: enforce time budgets by creating auto-blocks for exceeded members
    and removing blocks when a new day starts.

    Returns summary of actions taken.
    """
    # Get all enabled budgets
    result = await db.execute(
        select(TimeBudget).where(TimeBudget.enabled.is_(True))
    )
    budgets = list(result.scalars().all())

    blocked = 0
    unblocked = 0

    # Cache group owners for created_by FK
    group_owner_cache: dict[uuid.UUID, uuid.UUID] = {}

    for budget in budgets:
        member_today = _get_today_for_tz(budget.timezone)
        budget_minutes = (
            budget.weekend_minutes if _is_weekend(member_today) else budget.weekday_minutes
        )

        # Get today's usage
        usage_result = await db.execute(
            select(TimeBudgetUsage).where(
                TimeBudgetUsage.group_id == budget.group_id,
                TimeBudgetUsage.member_id == budget.member_id,
                TimeBudgetUsage.date == member_today,
            )
        )
        usage = usage_result.scalar_one_or_none()
        minutes_used = usage.minutes_used if usage else 0

        # Check for existing time-budget block
        existing_block_result = await db.execute(
            select(BlockRule).where(
                BlockRule.group_id == budget.group_id,
                BlockRule.member_id == budget.member_id,
                BlockRule.reason == "Time budget exceeded",
                BlockRule.active.is_(True),
            )
        )
        existing_block = existing_block_result.scalar_one_or_none()

        if minutes_used >= budget_minutes and budget_minutes > 0:
            # Exceeded — create block if not already blocked
            if not existing_block:
                # Resolve group owner for the created_by FK
                if budget.group_id not in group_owner_cache:
                    from src.groups.models import Group
                    g_result = await db.execute(
                        select(Group).where(Group.id == budget.group_id)
                    )
                    g = g_result.scalar_one_or_none()
                    group_owner_cache[budget.group_id] = g.owner_id if g else budget.group_id

                block = BlockRule(
                    id=uuid.uuid4(),
                    group_id=budget.group_id,
                    member_id=budget.member_id,
                    reason="Time budget exceeded",
                    active=True,
                    created_by=group_owner_cache[budget.group_id],
                )
                db.add(block)
                blocked += 1
                logger.info(
                    "time_budget_block_created",
                    member_id=str(budget.member_id),
                    minutes_used=minutes_used,
                    budget_minutes=budget_minutes,
                )
        else:
            # Not exceeded — remove block if exists
            if existing_block:
                existing_block.active = False
                unblocked += 1
                logger.info(
                    "time_budget_block_removed",
                    member_id=str(budget.member_id),
                )

    await db.flush()
    logger.info(
        "time_budget_enforcement_complete",
        budgets_checked=len(budgets),
        blocked=blocked,
        unblocked=unblocked,
    )
    return {"budgets_checked": len(budgets), "blocked": blocked, "unblocked": unblocked}


async def get_usage_history(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    days: int = 7,
) -> list[dict]:
    """Get daily usage history for a member.

    Returns a list of dicts with date, minutes_used, budget_minutes, exceeded.
    """
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(TimeBudgetUsage)
        .where(
            TimeBudgetUsage.group_id == group_id,
            TimeBudgetUsage.member_id == member_id,
            TimeBudgetUsage.date >= cutoff,
        )
        .order_by(TimeBudgetUsage.date.desc())
    )
    rows = list(result.scalars().all())

    return [
        {
            "date": str(row.date),
            "minutes_used": row.minutes_used,
            "budget_minutes": row.budget_minutes,
            "exceeded": row.exceeded,
        }
        for row in rows
    ]


async def get_time_budget(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> TimeBudget | None:
    """Get time budget config for a member."""
    result = await db.execute(
        select(TimeBudget).where(
            TimeBudget.group_id == group_id,
            TimeBudget.member_id == member_id,
        )
    )
    return result.scalar_one_or_none()


async def set_time_budget(
    db: AsyncSession,
    group_id: uuid.UUID,
    member_id: uuid.UUID,
    weekday_minutes: int = 60,
    weekend_minutes: int = 120,
    reset_hour: int = 0,
    tz: str = "UTC",
    enabled: bool = True,
    warn_at_percent: int = 75,
) -> TimeBudget:
    """Create or update a time budget for a member."""
    if weekday_minutes < 0 or weekend_minutes < 0:
        raise ValidationError("Minutes must be non-negative")
    if reset_hour < 0 or reset_hour > 23:
        raise ValidationError("Reset hour must be between 0 and 23")
    if warn_at_percent < 0 or warn_at_percent > 100:
        raise ValidationError("Warn percentage must be between 0 and 100")

    existing = await get_time_budget(db, group_id, member_id)
    if existing:
        existing.weekday_minutes = weekday_minutes
        existing.weekend_minutes = weekend_minutes
        existing.reset_hour = reset_hour
        existing.timezone = tz
        existing.enabled = enabled
        existing.warn_at_percent = warn_at_percent
        await db.flush()
        await db.refresh(existing)
        logger.info("time_budget_updated", member_id=str(member_id))
        return existing

    budget = TimeBudget(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        weekday_minutes=weekday_minutes,
        weekend_minutes=weekend_minutes,
        reset_hour=reset_hour,
        timezone=tz,
        enabled=enabled,
        warn_at_percent=warn_at_percent,
    )
    db.add(budget)
    await db.flush()
    await db.refresh(budget)
    logger.info("time_budget_created", member_id=str(member_id))
    return budget
