"""Billing API endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.billing.models import BudgetThreshold, LLMAccount, SpendRecord
from src.billing.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    LLMAccountResponse,
    PortalResponse,
    ProviderConnect,
    SubscribeRequest,
    SubscriptionStatus,
    ThresholdConfig,
    ThresholdResponse,
)
from src.billing.service import (
    connect_llm_account,
    create_checkout_session_for_group,
    create_subscription,
    create_threshold,
    disconnect_llm_account,
    revoke_llm_api_key,
    get_billing_portal_url,
    get_subscription,
    list_llm_accounts,
    list_thresholds,
)
from src.billing.stripe_client import StripeError, handle_webhook_event, verify_webhook_signature
from src.database import get_db
from src.dependencies import resolve_group_id as _gid
from src.exceptions import ValidationError as BhapiValidationError
from src.groups.models import GroupMember
from src.schemas import GroupContext

webhook_logger = structlog.get_logger()

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
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription status for a group."""
    subscription = await get_subscription(db, _gid(group_id, auth))
    return subscription


# ─── Stripe Checkout & Portal ────────────────────────────────────────────────


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    data: CheckoutRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for plan upgrade."""
    from src.auth.service import get_user_by_id

    user = await get_user_by_id(db, auth.user_id)
    gid = _gid(None, auth)

    try:
        result = await create_checkout_session_for_group(
            db=db,
            group_id=gid,
            user_email=user.email,
            user_name=user.display_name,
            plan_type=data.plan_type,
            billing_cycle=data.billing_cycle,
        )
    except StripeError as exc:
        raise BhapiValidationError(str(exc))

    return CheckoutResponse(session_id=result["session_id"], url=result["url"])


@router.get("/portal", response_model=PortalResponse)
async def get_billing_portal(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Stripe Billing Portal URL for managing subscription."""
    gid = _gid(None, auth)

    try:
        url = await get_billing_portal_url(db, gid)
    except StripeError as exc:
        raise BhapiValidationError(str(exc))

    return PortalResponse(url=url)


# ─── Stripe Webhooks ─────────────────────────────────────────────────────────


@router.post("/webhooks")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = verify_webhook_signature(payload, signature)
    except StripeError as exc:
        webhook_logger.warning("stripe_webhook_signature_failed", error=str(exc))
        raise BhapiValidationError(str(exc))

    result = await handle_webhook_event(event, db)
    webhook_logger.info(
        "stripe_webhook_processed",
        event_type=event.get("type"),
        action=result.get("action"),
    )
    return {"status": "ok"}


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
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List connected LLM accounts for a group."""
    accounts = await list_llm_accounts(db, _gid(group_id, auth))
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


@router.post("/llm-accounts/{account_id}/revoke")
async def revoke_account_key(
    account_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the API key for an LLM provider via their admin API.

    Attempts to revoke the key remotely, then clears local credentials.
    """
    revoked = await revoke_llm_api_key(db, account_id)
    return {
        "account_id": str(account_id),
        "provider_revoked": revoked,
        "credentials_cleared": True,
    }


# ─── Spend Tracking (BFF for frontend) ────────────────────────────────────────


def _period_range(period: str) -> tuple[datetime, datetime, str]:
    """Compute date range and label for a period."""
    now = datetime.now(timezone.utc)
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        label = "Today"
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        label = "This Week"
    else:  # month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = "This Month"
    return start, now, label


@router.get("/spend")
async def get_spend(
    group_id: UUID | None = Query(None, description="Group ID"),
    period: str = Query("month", pattern="^(day|week|month)$"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated spend summary matching frontend SpendSummary shape."""
    gid = _gid(group_id, auth)
    period_start, period_end, period_label = _period_range(period)

    # Total spend in period
    total_result = await db.execute(
        select(func.coalesce(func.sum(SpendRecord.amount), 0.0)).where(
            SpendRecord.group_id == gid,
            SpendRecord.period_start >= period_start,
        )
    )
    total_cost = float(total_result.scalar() or 0.0)

    # Budget
    budget_result = await db.execute(
        select(BudgetThreshold.amount).where(
            BudgetThreshold.group_id == gid,
            BudgetThreshold.member_id.is_(None),
        ).order_by(BudgetThreshold.created_at.desc()).limit(1)
    )
    budget_usd = float(budget_result.scalar() or 0.0)
    budget_remaining = max(budget_usd - total_cost, 0.0)
    budget_pct = (total_cost / budget_usd * 100.0) if budget_usd > 0 else 0.0

    # Days in period for average
    days = max((period_end - period_start).days, 1)
    avg_daily = total_cost / days

    # Members
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == gid)
    )
    members = list(members_result.scalars().all())
    member_names = {m.id: m.display_name for m in members}
    total_members = len(members)

    # Member breakdown
    member_spend_result = await db.execute(
        select(
            SpendRecord.member_id,
            func.coalesce(func.sum(SpendRecord.amount), 0.0).label("total"),
        ).where(
            SpendRecord.group_id == gid,
            SpendRecord.period_start >= period_start,
            SpendRecord.member_id.isnot(None),
        ).group_by(SpendRecord.member_id)
    )
    member_breakdown = []
    active_spenders = 0
    over_budget_count = 0
    for row in member_spend_result.all():
        mid, amount = row[0], float(row[1])
        if amount > 0:
            active_spenders += 1
        # Check member-level budget
        mb_result = await db.execute(
            select(BudgetThreshold.amount).where(
                BudgetThreshold.group_id == gid,
                BudgetThreshold.member_id == mid,
            ).limit(1)
        )
        member_limit = float(mb_result.scalar() or 0.0)
        if member_limit > 0 and amount > member_limit:
            over_budget_count += 1
        member_breakdown.append({
            "member_id": str(mid),
            "member_name": member_names.get(mid, "Unknown"),
            "cost_usd": round(amount, 2),
            "limit_usd": member_limit,
        })

    # Provider breakdown
    provider_result = await db.execute(
        select(
            LLMAccount.provider,
            func.coalesce(func.sum(SpendRecord.amount), 0.0).label("total"),
            func.count(SpendRecord.id).label("count"),
        ).join(LLMAccount, SpendRecord.llm_account_id == LLMAccount.id)
        .where(
            SpendRecord.group_id == gid,
            SpendRecord.period_start >= period_start,
        ).group_by(LLMAccount.provider)
        .order_by(func.sum(SpendRecord.amount).desc())
    )
    provider_breakdown = []
    for row in provider_result.all():
        prov, amount, count = row[0], float(row[1]), row[2]
        pct = (amount / total_cost * 100.0) if total_cost > 0 else 0.0
        provider_breakdown.append({
            "provider": prov,
            "cost_usd": round(amount, 2),
            "request_count": count,
            "percentage": round(pct, 1),
        })

    # Recent records
    records_result = await db.execute(
        select(SpendRecord)
        .where(
            SpendRecord.group_id == gid,
            SpendRecord.period_start >= period_start,
        ).order_by(SpendRecord.period_start.desc()).limit(20)
    )
    records = [
        {
            "id": str(r.id),
            "group_id": str(r.group_id),
            "member_id": str(r.member_id) if r.member_id else "",
            "member_name": member_names.get(r.member_id, "Unknown") if r.member_id else "",
            "provider": "",
            "model": r.model or "",
            "token_count": r.token_count or 0,
            "cost_usd": r.amount,
            "timestamp": r.period_start.isoformat() if r.period_start else "",
        }
        for r in records_result.scalars().all()
    ]

    return {
        "group_id": str(gid),
        "period": period,
        "period_label": period_label,
        "total_cost_usd": round(total_cost, 2),
        "budget_usd": budget_usd,
        "budget_remaining_usd": round(budget_remaining, 2),
        "budget_used_percentage": round(budget_pct, 1),
        "avg_daily_cost_usd": round(avg_daily, 2),
        "active_spenders": active_spenders,
        "total_members": total_members,
        "over_budget_count": over_budget_count,
        "member_breakdown": member_breakdown,
        "provider_breakdown": provider_breakdown,
        "records": records,
    }


@router.get("/spend/records")
async def get_spend_records(
    group_id: UUID | None = Query(None, description="Group ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member_id: UUID | None = Query(None),
    provider: str | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated spend records matching frontend PaginatedResponse."""
    gid = _gid(group_id, auth)

    # Members lookup
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == gid)
    )
    member_names = {m.id: m.display_name for m in members_result.scalars().all()}

    # Base query
    base = select(SpendRecord).where(SpendRecord.group_id == gid)
    count_q = select(func.count(SpendRecord.id)).where(SpendRecord.group_id == gid)

    if member_id:
        base = base.where(SpendRecord.member_id == member_id)
        count_q = count_q.where(SpendRecord.member_id == member_id)
    if provider:
        sub = select(LLMAccount.id).where(LLMAccount.provider == provider)
        base = base.where(SpendRecord.llm_account_id.in_(sub))
        count_q = count_q.where(SpendRecord.llm_account_id.in_(sub))

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(SpendRecord.period_start.desc()).offset(offset).limit(page_size)
    )
    items = [
        {
            "id": str(r.id),
            "group_id": str(r.group_id),
            "member_id": str(r.member_id) if r.member_id else "",
            "member_name": member_names.get(r.member_id, "") if r.member_id else "",
            "provider": "",
            "model": r.model or "",
            "token_count": r.token_count or 0,
            "cost_usd": r.amount,
            "timestamp": r.period_start.isoformat() if r.period_start else "",
        }
        for r in rows.scalars().all()
    ]
    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List budget thresholds for a group."""
    thresholds = await list_thresholds(db, _gid(group_id, auth))
    return thresholds
