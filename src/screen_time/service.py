"""Screen time business logic — rules, schedules, extension requests, usage evaluation."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import AgeTier, age_from_dob, get_tier_for_age
from src.device_agent.models import AppUsageRecord, ScreenTimeRecord
from src.exceptions import NotFoundError, RateLimitError, ValidationError
from src.groups.models import GroupMember
from src.screen_time.models import ExtensionRequest, ScreenTimeRule, ScreenTimeSchedule

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Age-tier extension request limits (requests per day)
# ---------------------------------------------------------------------------

EXTENSION_DAILY_LIMITS: dict[str, int] = {
    AgeTier.YOUNG: 0,      # 5-9: no self-extension
    AgeTier.PRETEEN: 2,    # 10-12: 2/day
    AgeTier.TEEN: 5,       # 13-15: 5/day
}

# Pending requests expire after 15 minutes
EXTENSION_EXPIRY_MINUTES = 15


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


async def create_rule(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    app_category: str,
    daily_limit_minutes: int,
    age_tier_enforcement: str = "warning_then_block",
    enabled: bool = True,
) -> ScreenTimeRule:
    """Create a screen time rule for a child."""
    rule = ScreenTimeRule(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        app_category=app_category,
        daily_limit_minutes=daily_limit_minutes,
        age_tier_enforcement=age_tier_enforcement,
        enabled=enabled,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    logger.info(
        "screen_time_rule_created",
        rule_id=str(rule.id),
        member_id=str(member_id),
        category=app_category,
        limit_minutes=daily_limit_minutes,
    )
    return rule


async def get_rules(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
) -> list[ScreenTimeRule]:
    """Get all rules for a child member."""
    result = await db.execute(
        select(ScreenTimeRule).where(
            ScreenTimeRule.group_id == group_id,
            ScreenTimeRule.member_id == member_id,
        ).order_by(ScreenTimeRule.created_at)
    )
    return list(result.scalars().all())


async def update_rule(
    db: AsyncSession,
    rule_id: UUID,
    data: dict,
    group_id: UUID | None = None,
) -> ScreenTimeRule:
    """Update a screen time rule."""
    q = select(ScreenTimeRule).where(ScreenTimeRule.id == rule_id)
    if group_id is not None:
        q = q.where(ScreenTimeRule.group_id == group_id)
    result = await db.execute(q)
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("ScreenTimeRule")

    allowed_fields = {
        "app_category", "daily_limit_minutes", "age_tier_enforcement", "enabled",
    }
    for field, value in data.items():
        if field in allowed_fields:
            setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)

    logger.info("screen_time_rule_updated", rule_id=str(rule_id))
    return rule


async def delete_rule(
    db: AsyncSession,
    rule_id: UUID,
    group_id: UUID | None = None,
) -> None:
    """Delete a screen time rule."""
    q = select(ScreenTimeRule).where(ScreenTimeRule.id == rule_id)
    if group_id is not None:
        q = q.where(ScreenTimeRule.group_id == group_id)
    result = await db.execute(q)
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("ScreenTimeRule")

    await db.delete(rule)
    await db.flush()

    logger.info("screen_time_rule_deleted", rule_id=str(rule_id))


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------


async def create_schedule(
    db: AsyncSession,
    rule_id: UUID,
    day_type: str,
    blocked_start,
    blocked_end,
    description: str | None = None,
) -> ScreenTimeSchedule:
    """Attach a time-of-day schedule to a screen time rule."""
    # Verify rule exists
    rule_result = await db.execute(
        select(ScreenTimeRule).where(ScreenTimeRule.id == rule_id)
    )
    if not rule_result.scalar_one_or_none():
        raise NotFoundError("ScreenTimeRule")

    schedule = ScreenTimeSchedule(
        id=uuid4(),
        rule_id=rule_id,
        day_type=day_type,
        blocked_start=blocked_start,
        blocked_end=blocked_end,
        description=description,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    logger.info(
        "screen_time_schedule_created",
        schedule_id=str(schedule.id),
        rule_id=str(rule_id),
        day_type=day_type,
    )
    return schedule


async def get_schedules(
    db: AsyncSession,
    rule_id: UUID,
) -> list[ScreenTimeSchedule]:
    """List all schedules for a rule."""
    result = await db.execute(
        select(ScreenTimeSchedule).where(
            ScreenTimeSchedule.rule_id == rule_id,
        ).order_by(ScreenTimeSchedule.created_at)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Usage Evaluation
# ---------------------------------------------------------------------------


async def evaluate_usage(
    db: AsyncSession,
    member_id: UUID,
) -> list[dict]:
    """Compare today's AppUsageRecord data against active rules.

    Returns per-category status: {category, used_minutes, limit_minutes,
    percent, enforcement_action}.
    """
    today = datetime.now(timezone.utc).date()
    start_dt = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    # Get all enabled rules for this member (across all groups)
    rules_result = await db.execute(
        select(ScreenTimeRule).where(
            ScreenTimeRule.member_id == member_id,
            ScreenTimeRule.enabled == True,  # noqa: E712
        )
    )
    rules = list(rules_result.scalars().all())

    if not rules:
        return []

    # Fetch today's usage records for this member
    usage_result = await db.execute(
        select(AppUsageRecord).where(
            AppUsageRecord.member_id == member_id,
            AppUsageRecord.started_at >= start_dt,
            AppUsageRecord.started_at < end_dt,
        )
    )
    usage_records = list(usage_result.scalars().all())

    # Aggregate minutes per category
    category_minutes: dict[str, float] = {}
    total_minutes = 0.0
    for rec in usage_records:
        category_minutes[rec.category] = (
            category_minutes.get(rec.category, 0.0) + rec.foreground_minutes
        )
        total_minutes += rec.foreground_minutes

    # Build evaluation result per rule
    evaluations = []
    for rule in rules:
        if rule.app_category == "all":
            used = total_minutes
        else:
            used = category_minutes.get(rule.app_category, 0.0)

        limit = rule.daily_limit_minutes
        percent = (used / limit * 100) if limit > 0 else 0.0

        # Determine enforcement action
        if percent >= 100:
            if rule.age_tier_enforcement == "hard_block":
                action = "block"
            elif rule.age_tier_enforcement == "warning_then_block":
                action = "block"
            else:  # warning_only
                action = "warn"
        elif percent >= 80:
            action = "warn"
        else:
            action = "allow"

        evaluations.append({
            "rule_id": str(rule.id),
            "category": rule.app_category,
            "used_minutes": round(used, 1),
            "limit_minutes": limit,
            "percent": round(percent, 1),
            "enforcement_action": action,
        })

    logger.info(
        "screen_time_evaluated",
        member_id=str(member_id),
        rules_count=len(rules),
    )
    return evaluations


# ---------------------------------------------------------------------------
# Extension Requests
# ---------------------------------------------------------------------------


async def _get_member_age_tier(db: AsyncSession, member_id: UUID) -> AgeTier | None:
    """Look up a member's age tier from their date of birth."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if not member or not member.date_of_birth:
        return None

    age = age_from_dob(member.date_of_birth)
    return get_tier_for_age(age)


async def create_extension_request(
    db: AsyncSession,
    member_id: UUID,
    rule_id: UUID,
    requested_minutes: int,
) -> ExtensionRequest:
    """Child requests more screen time. Enforces age-tier daily rate limit."""
    # Verify rule exists
    rule_result = await db.execute(
        select(ScreenTimeRule).where(ScreenTimeRule.id == rule_id)
    )
    if not rule_result.scalar_one_or_none():
        raise NotFoundError("ScreenTimeRule")

    # Get member's age tier
    tier = await _get_member_age_tier(db, member_id)

    # Default to preteen limits if tier is unknown
    daily_limit = EXTENSION_DAILY_LIMITS.get(tier, 2) if tier else 2

    if daily_limit == 0:
        raise ValidationError(
            "Screen time extension requests are not available for this age group. "
            "Please ask your parent directly."
        )

    # Count today's requests
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    count_result = await db.execute(
        select(func.count()).select_from(ExtensionRequest).where(
            ExtensionRequest.member_id == member_id,
            ExtensionRequest.requested_at >= today_start,
        )
    )
    today_count = count_result.scalar() or 0

    if today_count >= daily_limit:
        raise RateLimitError(
            f"Daily extension request limit ({daily_limit}) reached. "
            "Try again tomorrow."
        )

    now = datetime.now(timezone.utc)
    req = ExtensionRequest(
        id=uuid4(),
        member_id=member_id,
        rule_id=rule_id,
        requested_minutes=requested_minutes,
        status="pending",
        requested_at=now,
        responded_at=None,
        responded_by=None,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)

    logger.info(
        "extension_request_created",
        request_id=str(req.id),
        member_id=str(member_id),
        rule_id=str(rule_id),
        requested_minutes=requested_minutes,
        tier=str(tier),
    )
    return req


async def respond_to_extension(
    db: AsyncSession,
    request_id: UUID,
    parent_id: UUID,
    approved: bool,
) -> ExtensionRequest:
    """Parent approves or denies an extension request. Auto-denies expired requests."""
    result = await db.execute(
        select(ExtensionRequest).where(ExtensionRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise NotFoundError("ExtensionRequest")

    if req.status != "pending":
        raise ValidationError(
            f"Extension request is already {req.status} and cannot be modified."
        )

    now = datetime.now(timezone.utc)

    # Auto-deny if expired (>15 minutes old)
    requested_at = req.requested_at
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=timezone.utc)
    expiry_threshold = requested_at + timedelta(minutes=EXTENSION_EXPIRY_MINUTES)
    if now > expiry_threshold:
        req.status = "expired"
        req.responded_at = now
        req.responded_by = parent_id
        await db.flush()
        await db.refresh(req)
        logger.info(
            "extension_request_expired",
            request_id=str(request_id),
            parent_id=str(parent_id),
        )
        return req

    req.status = "approved" if approved else "denied"
    req.responded_at = now
    req.responded_by = parent_id

    await db.flush()
    await db.refresh(req)

    logger.info(
        "extension_request_responded",
        request_id=str(request_id),
        parent_id=str(parent_id),
        approved=approved,
        status=req.status,
    )
    return req


async def get_extension_requests(
    db: AsyncSession,
    member_id: UUID,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[ExtensionRequest], int]:
    """List extension requests for a member, optionally filtered by status."""
    base = select(ExtensionRequest).where(
        ExtensionRequest.member_id == member_id,
    )
    if status:
        base = base.where(ExtensionRequest.status == status)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(ExtensionRequest.requested_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total


# ---------------------------------------------------------------------------
# Weekly Report
# ---------------------------------------------------------------------------


async def get_weekly_report(
    db: AsyncSession,
    member_id: UUID,
) -> dict:
    """Aggregate ScreenTimeRecord data for the last 7 days.

    Returns daily totals, per-category breakdown, and summary stats.
    """
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)  # inclusive: 7 days total

    result = await db.execute(
        select(ScreenTimeRecord).where(
            ScreenTimeRecord.member_id == member_id,
            ScreenTimeRecord.date >= seven_days_ago,
            ScreenTimeRecord.date <= today,
        ).order_by(ScreenTimeRecord.date)
    )
    records = list(result.scalars().all())

    daily_totals = []
    category_totals: dict[str, float] = {}
    total_minutes = 0.0

    for rec in records:
        daily_totals.append({
            "date": rec.date.isoformat(),
            "total_minutes": rec.total_minutes,
            "category_breakdown": rec.category_breakdown or {},
        })
        total_minutes += rec.total_minutes
        if rec.category_breakdown:
            for cat, mins in rec.category_breakdown.items():
                category_totals[cat] = category_totals.get(cat, 0.0) + mins

    # Daily average over days that have data
    days_with_data = len(records)
    daily_average = (total_minutes / days_with_data) if days_with_data > 0 else 0.0

    logger.info(
        "weekly_report_generated",
        member_id=str(member_id),
        days_with_data=days_with_data,
        total_minutes=total_minutes,
    )

    return {
        "member_id": str(member_id),
        "period_start": seven_days_ago.isoformat(),
        "period_end": today.isoformat(),
        "total_minutes": round(total_minutes, 1),
        "daily_average_minutes": round(daily_average, 1),
        "days_with_data": days_with_data,
        "daily_totals": daily_totals,
        "category_totals": {k: round(v, 1) for k, v in category_totals.items()},
    }
