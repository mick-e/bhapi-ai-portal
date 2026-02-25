"""Stripe integration client — subscriptions, checkout, webhooks, billing portal.

Handles:
- Customer creation and management
- Checkout session creation
- Webhook event processing (created/updated/cancelled/payment_failed)
- Webhook signature validation
- Billing portal URL generation
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from src.config import get_settings

logger = structlog.get_logger()


class StripeError(Exception):
    """Stripe operation error."""


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
        raise StripeError(f"Failed to create customer: {exc}") from exc


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
        raise StripeError(f"Failed to get/create customer: {exc}") from exc


# ---------------------------------------------------------------------------
# Checkout session
# ---------------------------------------------------------------------------

# Plan → Stripe price ID mapping (configured in Stripe dashboard)
PLAN_PRICES = {
    "family_monthly": "price_family_monthly",
    "family_annual": "price_family_annual",
    "school_monthly": "price_school_monthly",
    "school_annual": "price_school_annual",
    "club_monthly": "price_club_monthly",
    "club_annual": "price_club_annual",
}


async def create_checkout_session(
    customer_id: str,
    plan_key: str,
    group_id: str,
    success_url: str = "https://bhapi.ai/billing/success?session_id={CHECKOUT_SESSION_ID}",
    cancel_url: str = "https://bhapi.ai/billing/cancel",
) -> dict:
    """Create a Stripe Checkout Session for subscription.

    Returns dict with session_id and url.
    """
    stripe = _get_stripe()

    price_id = PLAN_PRICES.get(plan_key)
    if not price_id:
        raise StripeError(f"Unknown plan: {plan_key}")

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"group_id": group_id, "plan_key": plan_key},
            subscription_data={
                "metadata": {"group_id": group_id, "plan_key": plan_key},
            },
        )

        logger.info(
            "stripe_checkout_created",
            session_id=session.id,
            plan=plan_key,
            group_id=group_id,
        )
        return {"session_id": session.id, "url": session.url}

    except stripe.StripeError as exc:
        raise StripeError(f"Failed to create checkout: {exc}") from exc


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
        raise StripeError(f"Failed to create portal session: {exc}") from exc


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
        raise StripeError(f"Invalid webhook signature: {exc}") from exc
    except ValueError as exc:
        raise StripeError(f"Invalid webhook payload: {exc}") from exc


async def handle_webhook_event(event: dict) -> dict:
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

    return await handler(data)


async def _handle_subscription_created(data: dict) -> dict:
    """Handle new subscription creation from Stripe."""
    sub_id = data.get("id")
    customer_id = data.get("customer")
    status = data.get("status")
    group_id = data.get("metadata", {}).get("group_id")
    plan_key = data.get("metadata", {}).get("plan_key", "unknown")

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
        "group_id": group_id,
        "plan_key": plan_key,
    }


async def _handle_subscription_updated(data: dict) -> dict:
    """Handle subscription update (plan change, renewal, etc.)."""
    sub_id = data.get("id")
    status = data.get("status")
    group_id = data.get("metadata", {}).get("group_id")

    # Extract current period end for renewal tracking
    period_end = data.get("current_period_end")
    if period_end:
        period_end = datetime.fromtimestamp(period_end, tz=timezone.utc).isoformat()

    logger.info(
        "stripe_subscription_updated",
        subscription_id=sub_id,
        status=status,
        group_id=group_id,
        period_end=period_end,
    )

    return {
        "action": "subscription_updated",
        "subscription_id": sub_id,
        "status": status,
        "group_id": group_id,
        "period_end": period_end,
    }


async def _handle_subscription_cancelled(data: dict) -> dict:
    """Handle subscription cancellation."""
    sub_id = data.get("id")
    group_id = data.get("metadata", {}).get("group_id")

    logger.info(
        "stripe_subscription_cancelled",
        subscription_id=sub_id,
        group_id=group_id,
    )

    return {
        "action": "subscription_cancelled",
        "subscription_id": sub_id,
        "group_id": group_id,
    }


async def _handle_payment_failed(data: dict) -> dict:
    """Handle failed payment (invoice.payment_failed)."""
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    sub_id = data.get("subscription")
    amount = data.get("amount_due", 0)

    logger.warning(
        "stripe_payment_failed",
        invoice_id=invoice_id,
        customer_id=customer_id,
        subscription_id=sub_id,
        amount=amount,
    )

    return {
        "action": "payment_failed",
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "subscription_id": sub_id,
        "amount": amount,
    }
