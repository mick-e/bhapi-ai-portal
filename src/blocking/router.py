"""Blocking API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.blocking.schemas import BlockRuleCreate, BlockRuleResponse, BlockStatus
from src.blocking.service import check_block_status, create_block_rule, get_active_blocks, revoke_block
from src.database import get_db
from src.schemas import GroupContext

router = APIRouter()


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
