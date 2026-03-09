"""Blocking API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.blocking.schemas import (
    AutoBlockRuleCreate,
    AutoBlockRuleRequest,
    AutoBlockRuleResponse,
    AutoBlockRuleUpdate,
    BlockRuleCreate,
    BlockRuleResponse,
    BlockStatus,
)
from src.blocking.service import (
    check_block_status,
    create_auto_block_rule,
    create_block_rule,
    delete_auto_block_rule,
    evaluate_group_auto_block_rules,
    get_active_blocks,
    list_active_auto_block_rules,
    list_active_rules,
    list_auto_block_rules,
    revoke_block,
    update_auto_block_rule,
)
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


@router.post("/rules", response_model=BlockRuleResponse, status_code=201)
async def create_rule(
    data: BlockRuleCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a block rule for a member."""
    rule = await create_block_rule(db, data, auth.user_id)
    return rule


@router.get("/rules", response_model=list[BlockRuleResponse])
async def list_rules(
    group_id: UUID = Query(...),
    member_id: UUID | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active block rules."""
    return await get_active_blocks(db, group_id, member_id)


@router.get("/active-rules")
async def get_active_rules(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active block rules for a group (polled by extension)."""
    rules = await list_active_rules(db, group_id)
    return {"rules": rules}


@router.delete("/rules/{rule_id}", response_model=BlockRuleResponse)
async def delete_rule(
    rule_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a block rule."""
    return await revoke_block(db, rule_id)


@router.get("/check/{member_id}")
async def check_block(
    member_id: UUID,
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a member is blocked (polled by extension)."""
    return await check_block_status(db, group_id, member_id)


# --- Auto block rule endpoints ---


@router.post("/auto-rules", response_model=AutoBlockRuleResponse, status_code=201)
async def create_auto_rule(
    data: AutoBlockRuleCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an automated blocking rule."""
    rule = await create_auto_block_rule(db, data, auth.user_id)
    return rule


@router.get("/auto-rules", response_model=list[AutoBlockRuleResponse])
async def list_auto_rules(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List automated blocking rules for a group."""
    return await list_auto_block_rules(db, group_id)


@router.patch("/auto-rules/{rule_id}", response_model=AutoBlockRuleResponse)
async def update_auto_rule(
    rule_id: UUID,
    data: AutoBlockRuleUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an automated blocking rule."""
    return await update_auto_block_rule(db, rule_id, data, auth.user_id)


@router.delete("/auto-rules/{rule_id}", status_code=204)
async def delete_auto_rule(
    rule_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an automated blocking rule."""
    await delete_auto_block_rule(db, rule_id, auth.user_id)
    return Response(status_code=204)


@router.post("/auto-rules/evaluate")
async def evaluate_rules(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate all auto-blocking rules for a group."""
    triggered = await evaluate_group_auto_block_rules(db, group_id)
    return {"triggered_rules": triggered, "count": len(triggered)}
