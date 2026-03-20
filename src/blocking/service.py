"""Blocking service — manage block rules for AI access."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blocking.models import AutoBlockRule, BlockRule
from src.blocking.schemas import AutoBlockRuleCreate, AutoBlockRuleRequest, AutoBlockRuleUpdate, BlockRuleCreate
from src.exceptions import NotFoundError

logger = structlog.get_logger()


async def create_block_rule(db: AsyncSession, data: BlockRuleCreate, user_id: UUID) -> BlockRule:
    """Create a new block rule for a member."""
    rule = BlockRule(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        platforms=data.platforms,
        reason=data.reason,
        active=True,
        created_by=user_id,
        expires_at=data.expires_at,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info("block_rule_created", rule_id=str(rule.id), member_id=str(data.member_id))
    return rule


async def get_active_blocks(db: AsyncSession, group_id: UUID, member_id: UUID | None = None) -> list[BlockRule]:
    """Get active block rules for a group, optionally filtered by member."""
    now = datetime.now(timezone.utc)
    query = select(BlockRule).where(
        BlockRule.group_id == group_id,
        BlockRule.active.is_(True),
    )
    if member_id:
        query = query.where(BlockRule.member_id == member_id)

    result = await db.execute(query)
    rules = list(result.scalars().all())

    # Filter out expired rules
    active = []
    for rule in rules:
        if rule.expires_at and rule.expires_at < now:
            rule.active = False
        else:
            active.append(rule)

    if len(active) != len(rules):
        await db.flush()

    return active


async def list_active_rules(db: AsyncSession, group_id: UUID) -> list[BlockRule]:
    """Get all active block rules for a group (polled by extension)."""
    return await get_active_blocks(db, group_id)


async def revoke_block(db: AsyncSession, rule_id: UUID) -> BlockRule:
    """Revoke (deactivate) a block rule."""
    result = await db.execute(select(BlockRule).where(BlockRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("BlockRule", str(rule_id))
    rule.active = False
    await db.flush()
    await db.refresh(rule)
    logger.info("block_rule_revoked", rule_id=str(rule_id))
    return rule


async def check_block_status(db: AsyncSession, group_id: UUID, member_id: UUID) -> dict:
    """Check if a member is currently blocked."""
    blocks = await get_active_blocks(db, group_id, member_id)
    return {"blocked": len(blocks) > 0, "rules": blocks}


# --- Auto block rule CRUD ---


async def create_auto_block_rule(
    db: AsyncSession, data: AutoBlockRuleCreate | AutoBlockRuleRequest, user_id: UUID | None = None
) -> AutoBlockRule:
    """Create a new automated blocking rule."""
    kwargs: dict = {
        "id": uuid4(),
        "group_id": data.group_id,
        "trigger_type": data.trigger_type,
        "active": True,
    }
    if user_id is not None:
        kwargs["created_by"] = user_id

    # Handle AutoBlockRuleRequest (new-style with name/trigger_config/action/enabled)
    if isinstance(data, AutoBlockRuleRequest):
        kwargs["name"] = data.name
        kwargs["trigger_config"] = data.trigger_config
        kwargs["action"] = data.action
        kwargs["enabled"] = data.enabled
    else:
        # AutoBlockRuleCreate (legacy-style with individual fields)
        kwargs["name"] = getattr(data, "name", "") or ""
        kwargs["trigger_config"] = getattr(data, "trigger_config", None)
        kwargs["action"] = getattr(data, "action", "block_all")
        kwargs["enabled"] = getattr(data, "enabled", True)
        kwargs["threshold"] = data.threshold
        kwargs["time_window_minutes"] = data.time_window_minutes
        kwargs["schedule_start"] = data.schedule_start
        kwargs["schedule_end"] = data.schedule_end
        kwargs["platforms"] = data.platforms
        kwargs["member_id"] = data.member_id

    rule = AutoBlockRule(**kwargs)
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info("auto_block_rule_created", rule_id=str(rule.id), trigger=data.trigger_type)
    return rule


async def list_auto_block_rules(
    db: AsyncSession, group_id: UUID
) -> list[AutoBlockRule]:
    """List all auto block rules for a group."""
    result = await db.execute(
        select(AutoBlockRule).where(AutoBlockRule.group_id == group_id)
    )
    return list(result.scalars().all())


async def list_active_auto_block_rules(
    db: AsyncSession, group_id: UUID
) -> list[AutoBlockRule]:
    """List only enabled auto block rules for a group."""
    result = await db.execute(
        select(AutoBlockRule).where(
            AutoBlockRule.group_id == group_id,
            AutoBlockRule.enabled.is_(True),
        )
    )
    return list(result.scalars().all())


async def update_auto_block_rule(
    db: AsyncSession, rule_id: UUID, data: AutoBlockRuleUpdate, user_id: UUID
) -> AutoBlockRule:
    """Update an auto block rule."""
    result = await db.execute(
        select(AutoBlockRule).where(AutoBlockRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("AutoBlockRule", str(rule_id))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    logger.info("auto_block_rule_updated", rule_id=str(rule_id))
    return rule


async def delete_auto_block_rule(
    db: AsyncSession, rule_id: UUID, user_id: UUID
) -> None:
    """Delete an auto block rule."""
    result = await db.execute(
        select(AutoBlockRule).where(AutoBlockRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("AutoBlockRule", str(rule_id))

    await db.delete(rule)
    await db.flush()
    logger.info("auto_block_rule_deleted", rule_id=str(rule_id))


# --- Auto block rule evaluation ---


async def evaluate_auto_block_rules(db: AsyncSession) -> dict:
    """Evaluate all active auto block rules and create block rules as needed."""

    result = await db.execute(
        select(AutoBlockRule).where(AutoBlockRule.active.is_(True))
    )
    rules = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    triggered = 0
    evaluated = 0

    for rule in rules:
        evaluated += 1
        fired = False

        if rule.trigger_type == "risk_event_count":
            fired = await _evaluate_risk_event_count(db, rule, now)
        elif rule.trigger_type == "spend_threshold":
            fired = await _evaluate_spend_threshold(db, rule, now)
        elif rule.trigger_type == "time_of_day":
            fired = await _evaluate_time_of_day(db, rule, now)

        if fired:
            rule.last_triggered_at = now
            triggered += 1

    await db.flush()
    logger.info(
        "auto_block_evaluation_complete",
        evaluated=evaluated,
        triggered=triggered,
    )
    return {"evaluated": evaluated, "triggered": triggered}


async def _evaluate_risk_event_count(
    db: AsyncSession, rule: AutoBlockRule, now: datetime
) -> bool:
    """Check if risk event count exceeds threshold within the time window."""
    from src.risk.models import RiskEvent

    if not rule.threshold or not rule.time_window_minutes:
        return False

    window_start = now - timedelta(minutes=rule.time_window_minutes)

    query = select(func.count()).select_from(RiskEvent).where(
        RiskEvent.group_id == rule.group_id,
        RiskEvent.created_at >= window_start,
    )
    if rule.member_id:
        query = query.where(RiskEvent.member_id == rule.member_id)

    result = await db.execute(query)
    count = result.scalar() or 0

    if count >= rule.threshold:
        # Avoid duplicate: check if an active block already exists for this auto rule
        existing = await db.execute(
            select(BlockRule).where(
                BlockRule.auto_rule_id == rule.id,
                BlockRule.active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            return False

        # Need a member_id for the block rule; if rule targets all members,
        # find distinct members from the risk events and block each
        if rule.member_id:
            member_ids = [rule.member_id]
        else:
            member_result = await db.execute(
                select(RiskEvent.member_id).where(
                    RiskEvent.group_id == rule.group_id,
                    RiskEvent.created_at >= window_start,
                ).distinct()
            )
            member_ids = [row[0] for row in member_result.all()]

        for mid in member_ids:
            block = BlockRule(
                id=uuid4(),
                group_id=rule.group_id,
                member_id=mid,
                platforms=rule.platforms,
                reason=f"Auto-blocked: {rule.trigger_type} threshold exceeded",
                active=True,
                created_by=rule.created_by,
                auto_rule_id=rule.id,
            )
            db.add(block)

        await db.flush()
        logger.info(
            "auto_block_triggered",
            rule_id=str(rule.id),
            trigger="risk_event_count",
            count=count,
        )
        return True

    return False


async def _evaluate_spend_threshold(
    db: AsyncSession, rule: AutoBlockRule, now: datetime
) -> bool:
    """Check if spend exceeds threshold within the time window."""
    from src.billing.models import SpendRecord

    if not rule.threshold:
        return False

    window_minutes = rule.time_window_minutes or 60 * 24 * 30  # default 30 days
    window_start = now - timedelta(minutes=window_minutes)

    query = select(func.sum(SpendRecord.amount)).where(
        SpendRecord.group_id == rule.group_id,
        SpendRecord.period_start >= window_start,
    )
    result = await db.execute(query)
    total = result.scalar() or 0

    if total >= rule.threshold:
        # Avoid duplicate
        existing = await db.execute(
            select(BlockRule).where(
                BlockRule.auto_rule_id == rule.id,
                BlockRule.active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            return False

        # For spend, block all members or the specific one
        if rule.member_id:
            member_ids = [rule.member_id]
        else:
            from src.groups.models import GroupMember
            member_result = await db.execute(
                select(GroupMember.id).where(
                    GroupMember.group_id == rule.group_id
                )
            )
            member_ids = [row[0] for row in member_result.all()]

        for mid in member_ids:
            block = BlockRule(
                id=uuid4(),
                group_id=rule.group_id,
                member_id=mid,
                platforms=rule.platforms,
                reason=f"Auto-blocked: spend threshold exceeded (${total:.2f})",
                active=True,
                created_by=rule.created_by,
                auto_rule_id=rule.id,
            )
            db.add(block)

        await db.flush()
        logger.info(
            "auto_block_triggered",
            rule_id=str(rule.id),
            trigger="spend_threshold",
            total_spend=total,
        )
        return True

    return False


async def _evaluate_time_of_day(
    db: AsyncSession, rule: AutoBlockRule, now: datetime
) -> bool:
    """Check if current time is within the scheduled block window."""
    if not rule.schedule_start or not rule.schedule_end:
        return False

    current_time = now.strftime("%H:%M")
    in_window = rule.schedule_start <= current_time <= rule.schedule_end

    # Check for existing auto-created block
    existing_result = await db.execute(
        select(BlockRule).where(
            BlockRule.auto_rule_id == rule.id,
            BlockRule.active.is_(True),
        )
    )
    existing_block = existing_result.scalar_one_or_none()

    if in_window and not existing_block:
        # Need member_id; for time_of_day without a specific member, block all
        if rule.member_id:
            member_ids = [rule.member_id]
        else:
            from src.groups.models import GroupMember
            member_result = await db.execute(
                select(GroupMember.id).where(
                    GroupMember.group_id == rule.group_id
                )
            )
            member_ids = [row[0] for row in member_result.all()]

        for mid in member_ids:
            block = BlockRule(
                id=uuid4(),
                group_id=rule.group_id,
                member_id=mid,
                platforms=rule.platforms,
                reason=f"Auto-blocked: scheduled block ({rule.schedule_start}-{rule.schedule_end})",
                active=True,
                created_by=rule.created_by,
                auto_rule_id=rule.id,
            )
            db.add(block)

        await db.flush()
        logger.info(
            "auto_block_triggered",
            rule_id=str(rule.id),
            trigger="time_of_day",
        )
        return True

    elif not in_window and existing_block:
        # Outside window — deactivate auto-created block
        existing_block.active = False
        await db.flush()
        logger.info(
            "auto_block_deactivated",
            rule_id=str(rule.id),
            trigger="time_of_day",
        )
        return False

    return False


async def set_bedtime_mode(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    start_hour: int,
    end_hour: int,
    tz: str = "UTC",
) -> AutoBlockRule:
    """Create or update a bedtime mode rule for a member.

    Uses time_of_day auto-block with reason 'Bedtime mode'.
    """
    if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
        from src.exceptions import ValidationError
        raise ValidationError("Hours must be between 0 and 23")

    # Check for existing bedtime rule
    existing_result = await db.execute(
        select(AutoBlockRule).where(
            AutoBlockRule.group_id == group_id,
            AutoBlockRule.member_id == member_id,
            AutoBlockRule.trigger_type == "time_of_day",
            AutoBlockRule.name == "Bedtime mode",
        )
    )
    existing = existing_result.scalar_one_or_none()

    schedule_start = f"{start_hour:02d}:00"
    schedule_end = f"{end_hour:02d}:00"

    if existing:
        existing.schedule_start = schedule_start
        existing.schedule_end = schedule_end
        existing.trigger_config = {
            "start_hour": start_hour,
            "end_hour": end_hour,
            "timezone": tz,
        }
        existing.enabled = True
        existing.active = True
        await db.flush()
        await db.refresh(existing)
        logger.info("bedtime_mode_updated", member_id=str(member_id))
        return existing

    # Resolve group owner for the created_by FK
    from src.groups.models import Group
    g_result = await db.execute(select(Group).where(Group.id == group_id))
    g = g_result.scalar_one_or_none()
    owner_id = g.owner_id if g else group_id

    rule = AutoBlockRule(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        name="Bedtime mode",
        trigger_type="time_of_day",
        trigger_config={
            "start_hour": start_hour,
            "end_hour": end_hour,
            "timezone": tz,
        },
        schedule_start=schedule_start,
        schedule_end=schedule_end,
        action="block_all",
        active=True,
        enabled=True,
        created_by=owner_id,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info("bedtime_mode_created", member_id=str(member_id))
    return rule


async def get_bedtime_mode(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> AutoBlockRule | None:
    """Get current bedtime mode config for a member."""
    result = await db.execute(
        select(AutoBlockRule).where(
            AutoBlockRule.group_id == group_id,
            AutoBlockRule.member_id == member_id,
            AutoBlockRule.trigger_type == "time_of_day",
            AutoBlockRule.name == "Bedtime mode",
        )
    )
    return result.scalar_one_or_none()


async def delete_bedtime_mode(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> None:
    """Disable bedtime mode for a member.

    Also deactivates any active blocks created by this rule.
    """
    result = await db.execute(
        select(AutoBlockRule).where(
            AutoBlockRule.group_id == group_id,
            AutoBlockRule.member_id == member_id,
            AutoBlockRule.trigger_type == "time_of_day",
            AutoBlockRule.name == "Bedtime mode",
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("Bedtime mode rule", f"member {member_id}")

    # Deactivate and unlink any blocks created by this rule
    blocks_result = await db.execute(
        select(BlockRule).where(
            BlockRule.auto_rule_id == rule.id,
        )
    )
    for block in blocks_result.scalars().all():
        block.active = False
        block.auto_rule_id = None

    await db.flush()
    await db.delete(rule)
    await db.flush()
    logger.info("bedtime_mode_deleted", member_id=str(member_id))


async def get_block_effectiveness(db: AsyncSession, group_id: UUID) -> dict:
    """Calculate blocking effectiveness metrics for a group."""
    from src.capture.models import CaptureEvent

    # Total active block rules
    rules_result = await db.execute(
        select(func.count()).select_from(BlockRule).where(
            BlockRule.group_id == group_id,
            BlockRule.active.is_(True),
        )
    )
    total_rules = rules_result.scalar() or 0

    # Count of blocked members (distinct member_ids with active rules)
    blocked_result = await db.execute(
        select(func.count(BlockRule.member_id.distinct())).where(
            BlockRule.group_id == group_id,
            BlockRule.active.is_(True),
        )
    )
    blocked_count = blocked_result.scalar() or 0

    # Total capture events for the group
    events_result = await db.execute(
        select(func.count()).select_from(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
        )
    )
    total_events = events_result.scalar() or 0

    # Calculate block rate percentage
    block_rate_pct = 0.0
    if total_events > 0:
        block_rate_pct = round((blocked_count / max(total_events, 1)) * 100, 2)

    return {
        "total_rules": total_rules,
        "blocked_count": blocked_count,
        "total_events": total_events,
        "block_rate_pct": block_rate_pct,
    }


async def evaluate_group_auto_block_rules(
    db: AsyncSession, group_id: UUID
) -> list[str]:
    """Evaluate all active+enabled rules for a group. Returns list of triggered rule IDs."""
    from src.billing.models import SpendRecord
    from src.risk.models import RiskEvent

    result = await db.execute(
        select(AutoBlockRule).where(
            AutoBlockRule.group_id == group_id,
            AutoBlockRule.enabled.is_(True),
            AutoBlockRule.active.is_(True),
        )
    )
    rules = list(result.scalars().all())
    triggered: list[str] = []

    now = datetime.now(timezone.utc)

    for rule in rules:
        config = rule.trigger_config or {}
        should_trigger = False

        if rule.trigger_type == "risk_event_count":
            threshold = config.get("threshold", rule.threshold or 5)
            window_hours = config.get("window_hours", 24)
            since = now - timedelta(hours=window_hours)
            count_result = await db.execute(
                select(func.count()).select_from(RiskEvent).where(
                    RiskEvent.group_id == group_id,
                    RiskEvent.created_at >= since,
                )
            )
            count = count_result.scalar() or 0
            should_trigger = count >= threshold

        elif rule.trigger_type == "spend_threshold":
            threshold_usd = config.get("threshold_usd", float(rule.threshold or 100))
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            spend_result = await db.execute(
                select(func.coalesce(func.sum(SpendRecord.amount), 0.0)).where(
                    SpendRecord.group_id == group_id,
                    SpendRecord.period_start >= period_start,
                )
            )
            total = float(spend_result.scalar() or 0.0)
            should_trigger = total >= threshold_usd

        elif rule.trigger_type == "time_of_day":
            blocked_start = config.get("start_hour", 22)
            blocked_end = config.get("end_hour", 6)
            current_hour = now.hour
            if blocked_start > blocked_end:
                should_trigger = current_hour >= blocked_start or current_hour < blocked_end
            else:
                should_trigger = blocked_start <= current_hour < blocked_end

        if should_trigger:
            rule.last_triggered_at = now
            triggered.append(str(rule.id))

    if triggered:
        await db.flush()

    return triggered
