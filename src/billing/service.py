"""Billing service — business logic for subscriptions, LLM accounts, and spend tracking."""

from datetime import datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import BudgetThreshold, LLMAccount, SpendRecord, Subscription
from src.billing.schemas import ProviderConnect, SubscribeRequest, ThresholdConfig
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ConflictError, NotFoundError, ValidationError

logger = structlog.get_logger()


# ─── Subscriptions ───────────────────────────────────────────────────────────


async def create_subscription(
    db: AsyncSession, data: SubscribeRequest
) -> Subscription:
    """Create a new subscription for a group."""
    # Check for existing active subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.group_id == data.group_id,
            Subscription.status.in_(["active", "trialing"]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("Group already has an active subscription")

    subscription = Subscription(
        id=uuid4(),
        group_id=data.group_id,
        plan_type=data.plan_type,
        billing_cycle=data.billing_cycle,
        status="active",
    )
    db.add(subscription)
    await db.flush()
    await db.refresh(subscription)

    logger.info(
        "subscription_created",
        subscription_id=str(subscription.id),
        group_id=str(data.group_id),
        plan_type=data.plan_type,
    )
    return subscription


async def create_checkout_session_for_group(
    db: AsyncSession,
    group_id: UUID,
    user_email: str,
    user_name: str,
    plan_type: str,
    billing_cycle: str,
) -> dict:
    """Create a Stripe Checkout Session for a group upgrade.

    Returns dict with session_id and url.
    """
    from src.billing.stripe_client import create_checkout_session, get_or_create_customer

    # Get or create Stripe customer
    customer_id = await get_or_create_customer(
        email=user_email,
        name=user_name,
        group_id=str(group_id),
    )

    # Build the plan key (e.g. "family_monthly")
    plan_key = f"{plan_type}_{billing_cycle}"

    result = await create_checkout_session(
        customer_id=customer_id,
        plan_key=plan_key,
        group_id=str(group_id),
    )

    logger.info(
        "checkout_session_created",
        group_id=str(group_id),
        plan_key=plan_key,
        session_id=result["session_id"],
    )
    return result


async def get_billing_portal_url(
    db: AsyncSession,
    group_id: UUID,
) -> str:
    """Get Stripe Billing Portal URL for a group's subscription."""
    from src.billing.stripe_client import create_portal_session

    # Find active subscription to get customer ID
    result = await db.execute(
        select(Subscription).where(
            Subscription.group_id == group_id,
            Subscription.stripe_customer_id.isnot(None),
        ).order_by(Subscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()
    if not subscription or not subscription.stripe_customer_id:
        raise NotFoundError("No active Stripe subscription", str(group_id))

    return await create_portal_session(customer_id=subscription.stripe_customer_id)


async def get_subscription(db: AsyncSession, group_id: UUID) -> Subscription:
    """Get the active subscription for a group."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.group_id == group_id,
        ).order_by(Subscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise NotFoundError("Subscription", str(group_id))
    return subscription


# ─── LLM Accounts ────────────────────────────────────────────────────────────


async def connect_llm_account(
    db: AsyncSession, data: ProviderConnect
) -> LLMAccount:
    """Connect an LLM provider account for spend tracking."""
    # Check for existing account with same provider
    result = await db.execute(
        select(LLMAccount).where(
            LLMAccount.group_id == data.group_id,
            LLMAccount.provider == data.provider,
            LLMAccount.status == "active",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"An active {data.provider} account is already connected for this group"
        )

    account = LLMAccount(
        id=uuid4(),
        group_id=data.group_id,
        provider=data.provider,
        credentials_encrypted=encrypt_credential(data.api_key),
        status="active",
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    logger.info(
        "llm_account_connected",
        account_id=str(account.id),
        group_id=str(data.group_id),
        provider=data.provider,
    )
    return account


async def get_llm_account_credential(
    db: AsyncSession, account_id: UUID
) -> str:
    """Get decrypted API key for an LLM account (used by spend sync)."""
    result = await db.execute(
        select(LLMAccount).where(LLMAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("LLM Account", str(account_id))
    if not account.credentials_encrypted:
        raise ValidationError("LLM account has no credentials stored")
    return decrypt_credential(account.credentials_encrypted)


async def list_llm_accounts(
    db: AsyncSession, group_id: UUID
) -> list[LLMAccount]:
    """List all LLM accounts for a group."""
    result = await db.execute(
        select(LLMAccount).where(LLMAccount.group_id == group_id)
    )
    return list(result.scalars().all())


async def disconnect_llm_account(
    db: AsyncSession, account_id: UUID
) -> LLMAccount:
    """Disconnect (deactivate) an LLM account."""
    result = await db.execute(
        select(LLMAccount).where(LLMAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise NotFoundError("LLM Account", str(account_id))

    account.status = "inactive"
    account.credentials_encrypted = None  # Clear credentials
    await db.flush()
    await db.refresh(account)

    logger.info("llm_account_disconnected", account_id=str(account_id))
    return account


# ─── Spend Tracking ──────────────────────────────────────────────────────────


async def get_spend_summary(
    db: AsyncSession,
    group_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Get aggregated spend summary for a group over a period."""
    result = await db.execute(
        select(SpendRecord).where(
            SpendRecord.group_id == group_id,
            SpendRecord.period_start >= period_start,
            SpendRecord.period_end <= period_end,
        )
    )
    records = list(result.scalars().all())

    total_amount = sum(r.amount for r in records)
    by_provider: dict[str, float] = {}
    by_member: dict[str, float] = {}
    by_model: dict[str, float] = {}

    for record in records:
        # Aggregate by provider via the LLM account
        # For now, we group by llm_account_id since we don't join
        account_key = str(record.llm_account_id)
        by_provider[account_key] = by_provider.get(account_key, 0.0) + record.amount

        if record.member_id:
            member_key = str(record.member_id)
            by_member[member_key] = by_member.get(member_key, 0.0) + record.amount

        if record.model:
            by_model[record.model] = by_model.get(record.model, 0.0) + record.amount

    return {
        "group_id": group_id,
        "period_start": period_start,
        "period_end": period_end,
        "total_amount": total_amount,
        "currency": "USD",
        "by_provider": by_provider,
        "by_member": by_member,
        "by_model": by_model,
        "record_count": len(records),
    }


async def get_spend_by_member(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[SpendRecord]:
    """Get spend records for a specific member."""
    result = await db.execute(
        select(SpendRecord).where(
            SpendRecord.group_id == group_id,
            SpendRecord.member_id == member_id,
        ).order_by(SpendRecord.period_start.desc())
    )
    return list(result.scalars().all())


async def get_spend_by_platform(
    db: AsyncSession, group_id: UUID, llm_account_id: UUID
) -> list[SpendRecord]:
    """Get spend records for a specific LLM platform account."""
    result = await db.execute(
        select(SpendRecord).where(
            SpendRecord.group_id == group_id,
            SpendRecord.llm_account_id == llm_account_id,
        ).order_by(SpendRecord.period_start.desc())
    )
    return list(result.scalars().all())


# ─── Budget Thresholds ───────────────────────────────────────────────────────


async def create_threshold(
    db: AsyncSession, data: ThresholdConfig
) -> BudgetThreshold:
    """Create a budget threshold."""
    threshold = BudgetThreshold(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        type=data.type,
        amount=data.amount,
        currency=data.currency,
        notify_at=data.notify_at,
    )
    db.add(threshold)
    await db.flush()
    await db.refresh(threshold)

    logger.info(
        "threshold_created",
        threshold_id=str(threshold.id),
        group_id=str(data.group_id),
        type=data.type,
        amount=data.amount,
    )
    return threshold


async def list_thresholds(
    db: AsyncSession, group_id: UUID
) -> list[BudgetThreshold]:
    """List all budget thresholds for a group."""
    result = await db.execute(
        select(BudgetThreshold).where(BudgetThreshold.group_id == group_id)
    )
    return list(result.scalars().all())
