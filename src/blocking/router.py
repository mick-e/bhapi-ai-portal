"""Blocking API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.blocking.approval import (
    approve_unblock,
    deny_unblock,
    list_pending_approvals,
    request_unblock,
)
from src.blocking.schemas import (
    AutoBlockRuleCreate,
    AutoBlockRuleResponse,
    AutoBlockRuleUpdate,
    BlockApprovalDecision,
    BlockApprovalRequest,
    BlockApprovalResponse,
    BlockEffectivenessResponse,
    BlockRuleCreate,
    BlockRuleResponse,
    BypassAttemptCreate,
    BypassAttemptResponse,
)
from src.blocking.service import (
    check_block_status,
    create_auto_block_rule,
    create_block_rule,
    delete_auto_block_rule,
    evaluate_group_auto_block_rules,
    get_active_blocks,
    get_block_effectiveness,
    list_active_rules,
    list_auto_block_rules,
    revoke_block,
    update_auto_block_rule,
)
from src.blocking.time_budget import TimeBudget as _TimeBudget  # noqa: F401 — register model
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
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


# --- Approval workflow endpoints ---


@router.post("/approval-request", response_model=BlockApprovalResponse, status_code=201)
async def create_approval_request(
    data: BlockApprovalRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an unblock request for approval."""
    return await request_unblock(
        db,
        group_id=data.group_id,
        block_rule_id=data.block_rule_id,
        member_id=data.member_id,
        reason=data.reason,
    )


@router.post("/approve/{approval_id}", response_model=BlockApprovalResponse)
async def approve_request(
    approval_id: UUID,
    data: BlockApprovalDecision,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve an unblock request."""
    return await approve_unblock(
        db,
        approval_id=approval_id,
        decided_by=auth.user_id,
        decision_note=data.decision_note,
    )


@router.post("/deny/{approval_id}", response_model=BlockApprovalResponse)
async def deny_request(
    approval_id: UUID,
    data: BlockApprovalDecision,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deny an unblock request."""
    return await deny_unblock(
        db,
        approval_id=approval_id,
        decided_by=auth.user_id,
        decision_note=data.decision_note,
    )


@router.get("/pending-approvals", response_model=list[BlockApprovalResponse])
async def get_pending_approvals(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending unblock requests for a group."""
    return await list_pending_approvals(db, group_id)


@router.get("/effectiveness", response_model=BlockEffectivenessResponse)
async def get_effectiveness(
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get blocking effectiveness metrics for a group."""
    return await get_block_effectiveness(db, group_id)


# ─── URL Filtering ──────────────────────────────────────────────────────────


@router.get("/url-filter/categories")
async def get_url_categories():
    """Get available URL filter categories (public)."""
    from src.blocking.url_filter import get_default_categories
    return {"categories": get_default_categories()}


@router.post("/url-filter/rules", status_code=201)
async def create_url_filter(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a URL filter rule."""
    from uuid import UUID as UUIDType

    from src.blocking.url_filter import create_filter_rule
    gid = _gid(None, auth)
    rule = await create_filter_rule(
        db, group_id=gid, category=data.get("category", ""),
        action=data.get("action", "block"),
        member_id=UUIDType(data["member_id"]) if data.get("member_id") else None,
        created_by=auth.user_id,
    )
    return {"id": str(rule.id), "category": rule.category, "action": rule.action}


@router.get("/url-filter/rules")
async def list_url_filters(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List URL filter rules."""
    from src.blocking.url_filter import list_filter_rules
    gid = _gid(None, auth)
    rules = await list_filter_rules(db, gid)
    return {"rules": [
        {"id": str(r.id), "category": r.category, "action": r.action, "active": r.active}
        for r in rules
    ]}


# --- Bypass detection (Phase 4 Task 23 — R-24) ---


@router.post(
    "/bypass-attempt",
    response_model=BypassAttemptResponse,
    status_code=201,
)
async def report_bypass_attempt(
    data: BypassAttemptCreate,
    request: Request,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Receive a bypass-attempt event from the extension or device agent.

    Persists the event, raises a high-severity alert to group admins, and
    auto-blocks the member when 3+ attempts occur in a 60-minute rolling
    window. Returns the persisted attempt with ``auto_blocked`` flag.
    """
    from src.blocking.vpn_detection import record_bypass_attempt

    gid = _gid(None, auth)
    user_agent = request.headers.get("user-agent")

    attempt = await record_bypass_attempt(
        db,
        group_id=gid,
        member_id=data.member_id,
        bypass_type=data.bypass_type,
        detection_signals=data.detection_signals,
        user_agent=user_agent,
    )
    return attempt


@router.post("/url-filter/check")
async def check_url_filter(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a URL should be filtered."""
    from uuid import UUID as UUIDType

    from src.blocking.url_filter import check_url
    gid = _gid(None, auth)
    return await check_url(
        db, gid, url=data.get("url", ""),
        member_id=UUIDType(data["member_id"]) if data.get("member_id") else None,
    )
