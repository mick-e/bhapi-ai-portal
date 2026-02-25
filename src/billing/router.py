"""Billing API endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.billing.schemas import (
    LLMAccountResponse,
    ProviderConnect,
    SpendRecordResponse,
    SpendSummary,
    SubscribeRequest,
    SubscriptionStatus,
    ThresholdConfig,
    ThresholdResponse,
)
from src.billing.service import (
    connect_llm_account,
    create_subscription,
    create_threshold,
    disconnect_llm_account,
    get_spend_by_member,
    get_spend_by_platform,
    get_spend_summary,
    get_subscription,
    list_llm_accounts,
    list_thresholds,
)
from src.database import get_db
from src.schemas import GroupContext

router = APIRouter()


# ─── Subscriptions ───────────────────────────────────────────────────────────


@router.post("/subscribe", response_model=SubscriptionStatus, status_code=201)
async def subscribe(
    data: SubscribeRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a subscription for a group (FR-031)."""
    subscription = await create_subscription(db, data)
    return subscription


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription status for a group."""
    subscription = await get_subscription(db, group_id)
    return subscription


# ─── LLM Accounts ────────────────────────────────────────────────────────────


@router.post("/llm-accounts", response_model=LLMAccountResponse, status_code=201)
async def connect_account(
    data: ProviderConnect,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect an LLM provider account (FR-032)."""
    account = await connect_llm_account(db, data)
    return account


@router.get("/llm-accounts", response_model=list[LLMAccountResponse])
async def list_accounts(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List connected LLM accounts for a group."""
    accounts = await list_llm_accounts(db, group_id)
    return accounts


@router.delete("/llm-accounts/{account_id}", response_model=LLMAccountResponse)
async def disconnect_account(
    account_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect an LLM provider account."""
    account = await disconnect_llm_account(db, account_id)
    return account


# ─── Spend Tracking ──────────────────────────────────────────────────────────


@router.get("/spend", response_model=SpendSummary)
async def get_spend(
    group_id: UUID = Query(..., description="Group ID"),
    period_start: datetime = Query(..., description="Period start (ISO 8601)"),
    period_end: datetime = Query(..., description="Period end (ISO 8601)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated spend summary for a group (FR-033)."""
    # Ensure timezone-aware datetimes
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)

    summary = await get_spend_summary(db, group_id, period_start, period_end)
    return summary


@router.get("/spend/member/{member_id}", response_model=list[SpendRecordResponse])
async def get_member_spend(
    member_id: UUID,
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get spend records for a specific member (FR-034)."""
    records = await get_spend_by_member(db, group_id, member_id)
    return records


@router.get("/spend/platform/{account_id}", response_model=list[SpendRecordResponse])
async def get_platform_spend(
    account_id: UUID,
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get spend records by LLM platform account."""
    records = await get_spend_by_platform(db, group_id, account_id)
    return records


# ─── Budget Thresholds ───────────────────────────────────────────────────────


@router.post("/thresholds", response_model=ThresholdResponse, status_code=201)
async def create_threshold_endpoint(
    data: ThresholdConfig,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a budget threshold (FR-035)."""
    threshold = await create_threshold(db, data)
    return threshold


@router.get("/thresholds", response_model=list[ThresholdResponse])
async def list_thresholds_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List budget thresholds for a group."""
    thresholds = await list_thresholds(db, group_id)
    return thresholds
