"""Screen time FastAPI router — rules, schedules, extension requests, evaluation."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.billing.feature_gate import check_feature_gate
from src.database import get_db
from src.dependencies import resolve_group_id
from src.schemas import GroupContext
from src.screen_time import schemas, service

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@router.post("/rules", response_model=schemas.ScreenTimeRuleResponse, status_code=201)
async def create_rule(
    data: schemas.ScreenTimeRuleCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent: create a screen time rule for a child."""
    gid = resolve_group_id(group_id, auth)
    if data.group_id is not None:
        gid = data.group_id
    rule = await service.create_rule(
        db,
        group_id=gid,
        member_id=data.member_id,
        app_category=data.app_category,
        daily_limit_minutes=data.daily_limit_minutes,
        age_tier_enforcement=data.age_tier_enforcement,
        enabled=data.enabled,
    )
    await db.commit()
    return rule


@router.get("/rules/{child_id}", response_model=schemas.ScreenTimeRuleListResponse)
async def get_rules(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent/device: get active screen time rules for a child."""
    gid = resolve_group_id(group_id, auth)
    rules = await service.get_rules(db, group_id=gid, member_id=child_id)
    return schemas.ScreenTimeRuleListResponse(items=rules, total=len(rules))


@router.put("/rules/{rule_id}", response_model=schemas.ScreenTimeRuleResponse)
async def update_rule(
    rule_id: UUID,
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent: update a screen time rule."""
    gid = resolve_group_id(group_id, auth)
    rule = await service.update_rule(db, rule_id=rule_id, data=data, group_id=gid)
    await db.commit()
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent: delete a screen time rule."""
    gid = resolve_group_id(group_id, auth)
    await service.delete_rule(db, rule_id=rule_id, group_id=gid)
    await db.commit()


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------


@router.post("/schedules", response_model=schemas.ScreenTimeScheduleResponse, status_code=201)
async def create_schedule(
    data: schemas.ScreenTimeScheduleCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent: create a time-of-day schedule for a rule."""
    schedule = await service.create_schedule(
        db,
        rule_id=data.rule_id,
        day_type=data.day_type,
        blocked_start=data.blocked_start,
        blocked_end=data.blocked_end,
        description=data.description,
    )
    await db.commit()
    return schedule


@router.get("/schedules/{rule_id}", response_model=list[schemas.ScreenTimeScheduleResponse])
async def get_schedules(
    rule_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Get schedules for a screen time rule."""
    schedules = await service.get_schedules(db, rule_id=rule_id)
    return schedules


# ---------------------------------------------------------------------------
# Usage Evaluation
# ---------------------------------------------------------------------------


@router.get("/evaluate/{child_id}")
async def evaluate_usage(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Evaluate current usage against rules for a child."""
    evaluations = await service.evaluate_usage(db, member_id=child_id)
    return {"member_id": str(child_id), "evaluations": evaluations}


# ---------------------------------------------------------------------------
# Extension Requests
# ---------------------------------------------------------------------------


@router.post("/extension-request", response_model=schemas.ExtensionRequestResponse, status_code=201)
async def create_extension_request(
    data: schemas.ExtensionRequestCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Child: request more screen time (age-tier rate limited)."""
    req = await service.create_extension_request(
        db,
        member_id=data.member_id,
        rule_id=data.rule_id,
        requested_minutes=data.requested_minutes,
    )
    await db.commit()
    return req


@router.put("/extension-request/{request_id}", response_model=schemas.ExtensionRequestResponse)
async def respond_to_extension(
    request_id: UUID,
    approved: bool,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Parent: approve or deny an extension request."""
    req = await service.respond_to_extension(
        db,
        request_id=request_id,
        parent_id=auth.user_id,
        approved=approved,
    )
    await db.commit()
    return req


@router.get("/extension-requests/{child_id}", response_model=schemas.ExtensionRequestListResponse)
async def get_extension_requests(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """List extension requests for a child."""
    items, total = await service.get_extension_requests(
        db,
        member_id=child_id,
        status=status,
        offset=offset,
        limit=limit,
    )
    return schemas.ExtensionRequestListResponse(
        items=items,
        total=total,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# Weekly Report
# ---------------------------------------------------------------------------


@router.get("/{child_id}/report")
async def get_weekly_report(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate("screen_time")),
):
    """Get a 7-day screen time report for a child."""
    return await service.get_weekly_report(db, member_id=child_id)
