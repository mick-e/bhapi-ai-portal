"""Blocking service — manage block rules for AI access."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blocking.models import BlockRule
from src.blocking.schemas import BlockRuleCreate
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
