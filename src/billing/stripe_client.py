"""Stripe integration client — subscriptions, checkout, webhooks, billing portal.

Handles:
- Customer creation and management
- Checkout session creation
- Webhook event processing (created/updated/cancelled/payment_failed)
- Webhook signature validation
- Billing portal URL generation
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import Subscription
from src.config import get_settings

logger = structlog.get_logger()


class StripeError(Exception):
    """Stripe operation error."""


def _sanitize_stripe_error(exc: Exception) -> str:
    """Strip sensitive details (API keys, internal IDs) from Stripe errors."""
    msg = str(exc)
    # Stripe errors often contain the API key — never expose it
    if "Invalid API Key" in msg or "sk_live" in msg or "sk_test" in msg:
        return "Payment service configuration error. Please contact support."
    if "No such" in msg:
        return "Payment resource not found. Please try again or contact support."
    return "Payment service error. Please try again later."


def _get_stripe():
    """Lazy-import and configure the Stripe module."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise StripeError("STRIPE_SECRET_KEY not configured")

    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------

async def create_customer(
    email: str,
    name: str,
    metadata: dict | None = None,
) -> str:
    """Create a Stripe customer. Returns the customer ID."""
    stripe = _get_stripe()

    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {},
        )
        logger.info("stripe_customer_created", customer_id=customer.id, email=email)
        return customer.id
    except stripe.StripeError as exc:
        logger.error("stripe_customer_create_error", error=str(exc))
        raise StripeError(_sanitize_stripe_error(exc)) from exc


async def get_or_create_customer(
    email: str,
    name: str,
    group_id: str,
) -> str:
    """Get existing Stripe customer by email or create a new one."""
    stripe = _get_stripe()

    try:
        customers = stripe.Customer.list(email=email, limit=1)
        if customers.data:
            return customers.data[0].id
        return await create_customer(email, name, metadata={"group_id": group_id})
    except stripe.StripeError as exc:
        raise StripeError(_sanitize_stripe_error(exc)) from exc


# ---------------------------------------------------------------------------
# Checkout session
# ---------------------------------------------------------------------------

# Plan → Stripe price ID mapping (configured in Stripe dashboard)
PLAN_PRICES = {
    "family_monthly": os.environ.get("STRIPE_PRICE_FAMILY_MONTHLY", "price_family_monthly"),
    "family_annual": os.environ.get("STRIPE_PRICE_FAMILY_ANNUAL", "price_family_annual"),
    "school_monthly": os.environ.get("STRIPE_PRICE_SCHOOL_MONTHLY", "price_school_monthly"),
    "school_annual": os.environ.get("STRIPE_PRICE_SCHOOL_ANNUAL", "price_school_annual"),
    "club_monthly": os.environ.get("STRIPE_PRICE_CLUB_MONTHLY", "price_club_monthly"),
    "club_annual": os.environ.get("STRIPE_PRICE_CLUB_ANNUAL", "price_club_annual"),
}

# Per-seat plans (quantity = member count)
PER_SEAT_PLANS = {"school", "club"}

# Plans that require contacting sales for custom pricing (none currently)
CONTACT_SALES_PLANS: set[str] = set()


async def create_checkout_session(
    customer_id: str,
    plan_key: str,
    group_id: str,
    seat_count: int = 1,
    is_new_subscription: bool = True,
    success_url: str = "https://bhapi.ai/billing/success?session_id={CHECKOUT_SESSION_ID}",
    cancel_url: str = "https://bhapi.ai/billing/cancel",
) -> dict:
    """Create a Stripe Checkout Session for subscription.

    For school/club plans, seat_count sets the per-seat quantity.
    Returns dict with session_id and url.
    """
    stripe = _get_stripe()

    # Check if this is a contact-sales plan
    plan_base = plan_key.rsplit("_", 1)[0] if "_" in plan_key else plan_key
    if plan_base in CONTACT_SALES_PLANS:
        raise StripeError(f"Plan '{plan_base}' requires custom pricing — contact sales")

    price_id = PLAN_PRICES.get(plan_key)
    if not price_id:
        raise StripeError(f"Unknown plan: {plan_key}")

    # Per-seat plans use member count as quantity
    quantity = max(seat_count, 1) if plan_base in PER_SEAT_PLANS else 1

    # Trial for new subscriptions
    from src.constants import FREE_TRIAL_DAYS
    subscription_data: dict = {
        "metadata": {"group_id": group_id, "plan_key": plan_key},
    }
    if is_new_subscription:
        subscription_data["trial_period_days"] = FREE_TRIAL_DAYS

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": quantity}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"group_id": group_id, "plan_key": plan_key},
            subscription_data=subscription_data,
        )

        logger.info(
            "stripe_checkout_created",
            session_id=session.id,
            plan=plan_key,
            group_id=group_id,
        )
        return {"session_id": session.id, "url": session.url}

    except stripe.StripeError as exc:
        raise StripeError(_sanitize_stripe_error(exc)) from exc


# ---------------------------------------------------------------------------
# Billing portal
# ---------------------------------------------------------------------------

async def create_portal_session(
    customer_id: str,
    return_url: str = "https://bhapi.ai/billing",
) -> str:
    """Create a Stripe Billing Portal session. Returns the portal URL."""
    stripe = _get_stripe()

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except stripe.StripeError as exc:
        raise StripeError(_sanitize_stripe_error(exc)) from exc


# ---------------------------------------------------------------------------
# Webhook processing
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str) -> dict:
    """Verify Stripe webhook signature and return the event.

    Raises StripeError if signature is invalid.
    """
    stripe = _get_stripe()
    settings = get_settings()

    if not settings.stripe_webhook_secret:
        raise StripeError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        return event
    except stripe.SignatureVerificationError as exc:
        raise StripeError("Invalid webhook signature") from exc
    except ValueError as exc:
        raise StripeError("Invalid webhook payload") from exc


async def handle_webhook_event(event: dict, db: AsyncSession) -> dict:
    """Process a verified Stripe webhook event.

    Supported events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed

    Returns a dict with the action taken.
    """
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    handlers = {
        "customer.subscription.created": _handle_subscription_created,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_cancelled,
        "invoice.payment_failed": _handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.debug("stripe_webhook_unhandled", event_type=event_type)
        return {"action": "ignored", "event_type": event_type}

    return await handler(data, db)


async def _handle_subscription_created(data: dict, db: AsyncSession) -> dict:
    """Handle new subscription creation from Stripe."""
    sub_id = data.get("id")
    customer_id = data.get("customer")
    status = data.get("status")
    group_id_str = data.get("metadata", {}).get("group_id")
    group_id = UUID(group_id_str) if group_id_str else None
    plan_key = data.get("metadata", {}).get("plan_key", "unknown")

    # Parse plan_type and billing_cycle from plan_key (e.g. "family_monthly")
    parts = plan_key.rsplit("_", 1) if "_" in plan_key else [plan_key, "monthly"]
    plan_type = parts[0]
    billing_cycle = parts[1] if len(parts) > 1 else "monthly"

    # Parse current_period_end and trial_end
    period_end_ts = data.get("current_period_end")
    current_period_end = (
        datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        if period_end_ts
        else None
    )
    trial_end_ts = data.get("trial_end")
    trial_end = (
        datetime.fromtimestamp(trial_end_ts, tz=timezone.utc)
        if trial_end_ts
        else None
    )

    # Upsert: find existing subscription by stripe_subscription_id or group_id
    existing = None
    if sub_id:
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == sub_id
            )
        )
        existing = result.scalar_one_or_none()

    if not existing and group_id:
        result = await db.execute(
            select(Subscription).where(Subscription.group_id == group_id)
        )
        existing = result.scalar_one_or_none()

    if existing:
        existing.stripe_subscription_id = sub_id
        existing.stripe_customer_id = customer_id
        existing.plan_type = plan_type
        existing.billing_cycle = billing_cycle
        existing.status = status
        existing.current_period_end = current_period_end
        existing.trial_end = trial_end
    else:
        subscription = Subscription(
            id=uuid4(),
            group_id=group_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=sub_id,
            plan_type=plan_type,
            billing_cycle=billing_cycle,
            status=status,
            current_period_end=current_period_end,
            trial_end=trial_end,
        )
        db.add(subscription)

    await db.flush()

    logger.info(
        "stripe_subscription_created",
        subscription_id=sub_id,
        customer_id=customer_id,
        status=status,
        group_id=group_id,
        plan=plan_key,
    )

    return {
        "action": "subscription_created",
        "subscription_id": sub_id,
        "customer_id": customer_id,
        "status": status,
        "group_id": str(group_id) if group_id else None,
        "plan_key": plan_key,
    }


async def _handle_subscription_updated(data: dict, db: AsyncSession) -> dict:
    """Handle subscription update (plan change, renewal, etc.)."""
    sub_id = data.get("id")
    status = data.get("status")
    group_id = data.get("metadata", {}).get("group_id")

    # Extract current period end for renewal tracking
    period_end_ts = data.get("current_period_end")
    current_period_end = (
        datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
        if period_end_ts
        else None
    )
    period_end_iso = current_period_end.isoformat() if current_period_end else None

    # Update existing subscription in DB
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == sub_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.status = status
        if current_period_end:
            existing.current_period_end = current_period_end
        await db.flush()
        logger.info(
            "stripe_subscription_updated",
            subscription_id=sub_id,
            status=status,
            group_id=group_id,
            period_end=period_end_iso,
        )
    else:
        logger.warning(
            "stripe_subscription_updated_not_found",
            subscription_id=sub_id,
            status=status,
            group_id=group_id,
        )

    return {
        "action": "subscription_updated",
        "subscription_id": sub_id,
        "status": status,
        "group_id": group_id,
        "period_end": period_end_iso,
    }


async def _handle_subscription_cancelled(data: dict, db: AsyncSession) -> dict:
    """Handle subscription cancellation."""
    sub_id = data.get("id")
    group_id = data.get("metadata", {}).get("group_id")

    # Set status to cancelled in DB
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == sub_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.status = "cancelled"
        await db.flush()
        logger.info(
            "stripe_subscription_cancelled",
            subscription_id=sub_id,
            group_id=group_id,
        )
    else:
        logger.warning(
            "stripe_subscription_cancelled_not_found",
            subscription_id=sub_id,
            group_id=group_id,
        )

    return {
        "action": "subscription_cancelled",
        "subscription_id": sub_id,
        "group_id": group_id,
    }


async def _handle_payment_failed(data: dict, db: AsyncSession) -> dict:
    """Handle failed payment (invoice.payment_failed)."""
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    sub_id = data.get("subscription")
    amount = data.get("amount_due", 0)

    # Set subscription status to past_due
    if sub_id:
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == sub_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.status = "past_due"
            await db.flush()
            logger.warning(
                "stripe_payment_failed",
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=sub_id,
                amount=amount,
            )
        else:
            logger.warning(
                "stripe_payment_failed_subscription_not_found",
                invoice_id=invoice_id,
                customer_id=customer_id,
                subscription_id=sub_id,
                amount=amount,
            )
    else:
        logger.warning(
            "stripe_payment_failed_no_subscription",
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=amount,
        )

    return {
        "action": "payment_failed",
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "subscription_id": sub_id,
        "amount": amount,
    }
