"""Approval service — unblock request workflow."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.blocking.approval_models import BlockApproval
from src.blocking.models import BlockRule
from src.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


async def request_unblock(
    db: AsyncSession,
    group_id: UUID,
    block_rule_id: UUID,
    member_id: UUID,
    reason: str,
) -> BlockApproval:
    """Submit a request to unblock a member."""
    # Verify the block rule exists
    result = await db.execute(
        select(BlockRule).where(
            BlockRule.id == block_rule_id,
            BlockRule.group_id == group_id,
            BlockRule.active.is_(True),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("BlockRule", str(block_rule_id))

    # Check for existing pending request for this rule
    existing = await db.execute(
        select(BlockApproval).where(
            BlockApproval.block_rule_id == block_rule_id,
            BlockApproval.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationError("A pending unblock request already exists for this rule")

    approval = BlockApproval(
        id=uuid4(),
        group_id=group_id,
        block_rule_id=block_rule_id,
        member_id=member_id,
        reason=reason,
        status="pending",
    )
    db.add(approval)
    await db.flush()
    await db.refresh(approval)
    logger.info(
        "unblock_request_created",
        approval_id=str(approval.id),
        block_rule_id=str(block_rule_id),
    )
    return approval


async def approve_unblock(
    db: AsyncSession,
    approval_id: UUID,
    decided_by: UUID,
    decision_note: str | None = None,
) -> BlockApproval:
    """Approve an unblock request and deactivate the block rule."""
    result = await db.execute(
        select(BlockApproval).where(BlockApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise NotFoundError("BlockApproval", str(approval_id))

    if approval.status != "pending":
        raise ValidationError(f"Approval is already {approval.status}")

    approval.status = "approved"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_note = decision_note

    # Deactivate the associated block rule
    rule_result = await db.execute(
        select(BlockRule).where(BlockRule.id == approval.block_rule_id)
    )
    rule = rule_result.scalar_one_or_none()
    if rule:
        rule.active = False

    await db.flush()
    await db.refresh(approval)
    logger.info(
        "unblock_approved",
        approval_id=str(approval_id),
        block_rule_id=str(approval.block_rule_id),
        decided_by=str(decided_by),
    )
    return approval


async def deny_unblock(
    db: AsyncSession,
    approval_id: UUID,
    decided_by: UUID,
    decision_note: str | None = None,
) -> BlockApproval:
    """Deny an unblock request."""
    result = await db.execute(
        select(BlockApproval).where(BlockApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise NotFoundError("BlockApproval", str(approval_id))

    if approval.status != "pending":
        raise ValidationError(f"Approval is already {approval.status}")

    approval.status = "denied"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_note = decision_note

    await db.flush()
    await db.refresh(approval)
    logger.info(
        "unblock_denied",
        approval_id=str(approval_id),
        block_rule_id=str(approval.block_rule_id),
        decided_by=str(decided_by),
    )
    return approval


async def list_pending_approvals(
    db: AsyncSession,
    group_id: UUID,
) -> list[BlockApproval]:
    """List all pending unblock requests for a group."""
    result = await db.execute(
        select(BlockApproval).where(
            BlockApproval.group_id == group_id,
            BlockApproval.status == "pending",
        )
    )
    return list(result.scalars().all())
