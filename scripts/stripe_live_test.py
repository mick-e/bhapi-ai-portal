#!/usr/bin/env python3
"""Stripe integration verification script (test mode only).

Walks through Stripe integration verification steps using the Stripe API
in test mode. Refuses to run against live keys.

Usage:
    STRIPE_SECRET_KEY=sk_test_... python scripts/stripe_live_test.py

Requires: pip install stripe
"""

import os
import sys
import time

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
INFO = "[INFO]"

# Plan price mappings — replace with actual Stripe price IDs when configured
PLAN_PRICES = {
    "family_monthly": os.environ.get("STRIPE_PRICE_FAMILY_MONTHLY", ""),
    "family_annual": os.environ.get("STRIPE_PRICE_FAMILY_ANNUAL", ""),
    "school_monthly": os.environ.get("STRIPE_PRICE_SCHOOL_MONTHLY", ""),
    "school_annual": os.environ.get("STRIPE_PRICE_SCHOOL_ANNUAL", ""),
    "club_monthly": os.environ.get("STRIPE_PRICE_CLUB_MONTHLY", ""),
    "club_annual": os.environ.get("STRIPE_PRICE_CLUB_ANNUAL", ""),
}

test_customers: list[str] = []
test_subscriptions: list[str] = []


def log(status: str, message: str, detail: str = "") -> None:
    """Print a formatted log line."""
    line = f"  {status} {message}"
    if detail:
        line += f" — {detail}"
    print(line)


def section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def preflight_checks() -> bool:
    """Verify environment is safe for testing."""
    section("1. Pre-flight Checks")

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        log(FAIL, "STRIPE_SECRET_KEY not set")
        print("\n  Set STRIPE_SECRET_KEY=sk_test_... and re-run.")
        return False

    if key.startswith("sk_live_"):
        log(FAIL, "REFUSING to run against live Stripe key")
        print("\n  This script only runs in test mode (sk_test_...).")
        return False

    if not key.startswith("sk_test_"):
        log(FAIL, f"Unexpected key prefix: {key[:10]}...")
        return False

    log(PASS, "STRIPE_SECRET_KEY is a test key")

    try:
        import stripe
        stripe.api_key = key
        log(PASS, f"Stripe SDK loaded (version {stripe.VERSION})")
    except ImportError:
        log(FAIL, "stripe package not installed", "pip install stripe")
        return False

    # Verify API connectivity
    try:
        account = stripe.Account.retrieve()
        log(PASS, f"Connected to Stripe account: {account.get('business_profile', {}).get('name', account.id)}")
    except stripe.StripeError as e:
        log(FAIL, f"Stripe API error: {e}")
        return False

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret:
        if webhook_secret.startswith("whsec_"):
            log(PASS, "STRIPE_WEBHOOK_SECRET is set")
        else:
            log(FAIL, "STRIPE_WEBHOOK_SECRET has unexpected format")
    else:
        log(SKIP, "STRIPE_WEBHOOK_SECRET not set (webhook tests will be skipped)")

    return True


def test_customer_creation() -> str | None:
    """Create a test customer."""
    section("2. Customer Creation")
    import stripe

    try:
        customer = stripe.Customer.create(
            email="test-bhapi-verification@example.com",
            name="Bhapi Test Customer",
            metadata={"source": "stripe_live_test.py", "test_run": str(int(time.time()))},
        )
        test_customers.append(customer.id)
        log(PASS, f"Created customer: {customer.id}")
        log(INFO, f"Email: {customer.email}")

        # Verify retrieval
        retrieved = stripe.Customer.retrieve(customer.id)
        assert retrieved.id == customer.id
        log(PASS, "Customer retrieval verified")

        return customer.id
    except Exception as e:
        log(FAIL, f"Customer creation failed: {e}")
        return None


def test_checkout_sessions(customer_id: str) -> None:
    """Create checkout sessions for each plan type."""
    section("3. Checkout Sessions")
    import stripe

    configured_prices = {k: v for k, v in PLAN_PRICES.items() if v}

    if not configured_prices:
        log(SKIP, "No STRIPE_PRICE_* env vars set — creating generic checkout session")

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Bhapi Family Plan (Test)"},
                        "unit_amount": 999,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url="https://bhapi.ai/billing?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://bhapi.ai/billing?cancelled=true",
                metadata={"test": "true"},
            )
            log(PASS, f"Checkout session created: {session.id}")
            log(INFO, f"URL: {session.url[:80]}...")
        except Exception as e:
            log(FAIL, f"Checkout session failed: {e}")
        return

    for plan_name, price_id in configured_prices.items():
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url="https://bhapi.ai/billing?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://bhapi.ai/billing?cancelled=true",
                metadata={"plan": plan_name, "test": "true"},
            )
            log(PASS, f"{plan_name}: session {session.id}")
        except Exception as e:
            log(FAIL, f"{plan_name}: {e}")


def test_subscription_lifecycle(customer_id: str) -> None:
    """Test subscription creation and status transitions."""
    section("4. Subscription Lifecycle")
    import stripe

    # Attach a test payment method
    try:
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2027,
                "cvc": "314",
            },
        )
        stripe.PaymentMethod.attach(pm.id, customer=customer_id)
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": pm.id},
        )
        log(PASS, f"Test payment method attached: {pm.id}")
    except Exception as e:
        log(FAIL, f"Payment method setup failed: {e}")
        return

    # Create subscription with trial
    try:
        sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Bhapi Test Plan"},
                    "unit_amount": 999,
                    "recurring": {"interval": "month"},
                },
            }],
            trial_period_days=14,
            metadata={"test": "true"},
        )
        test_subscriptions.append(sub.id)
        log(PASS, f"Subscription created: {sub.id}")
        log(INFO, f"Status: {sub.status}")
        assert sub.status == "trialing", f"Expected 'trialing', got '{sub.status}'"
        log(PASS, "Status is 'trialing' (14-day trial)")
    except Exception as e:
        log(FAIL, f"Subscription creation failed: {e}")
        return

    # Cancel subscription
    try:
        cancelled = stripe.Subscription.cancel(sub.id)
        log(PASS, f"Subscription cancelled, status: {cancelled.status}")
    except Exception as e:
        log(FAIL, f"Subscription cancellation failed: {e}")


def test_portal_session(customer_id: str) -> None:
    """Create a billing portal session."""
    section("5. Billing Portal Session")
    import stripe

    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url="https://bhapi.ai/settings",
        )
        log(PASS, f"Portal session created")
        log(INFO, f"URL: {portal.url[:80]}...")
        assert portal.url.startswith("https://"), "Portal URL should be HTTPS"
        log(PASS, "Portal URL is HTTPS")
    except Exception as e:
        log(FAIL, f"Portal session failed: {e}")


def test_webhook_events() -> None:
    """List recent webhook events (informational)."""
    section("6. Webhook Events")
    import stripe

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        log(SKIP, "STRIPE_WEBHOOK_SECRET not set — skipping webhook tests")
        log(INFO, "To test webhooks: stripe listen --forward-to localhost:8000/api/v1/billing/webhooks")
        return

    try:
        events = stripe.Event.list(limit=10)
        log(PASS, f"Retrieved {len(events.data)} recent events")
        for evt in events.data[:5]:
            log(INFO, f"  {evt.type} ({evt.id})")

        # Verify expected event types exist
        event_types = {e.type for e in events.data}
        expected = ["customer.created", "customer.subscription.created"]
        for et in expected:
            if et in event_types:
                log(PASS, f"Event type '{et}' found")
            else:
                log(INFO, f"Event type '{et}' not in recent events (may need to trigger)")
    except Exception as e:
        log(FAIL, f"Event listing failed: {e}")


def cleanup() -> None:
    """Delete test customers and subscriptions."""
    section("7. Cleanup")
    import stripe

    for sub_id in test_subscriptions:
        try:
            stripe.Subscription.cancel(sub_id)
            log(PASS, f"Cancelled subscription: {sub_id}")
        except Exception:
            pass  # May already be cancelled

    for cust_id in test_customers:
        try:
            stripe.Customer.delete(cust_id)
            log(PASS, f"Deleted customer: {cust_id}")
        except Exception as e:
            log(FAIL, f"Failed to delete customer {cust_id}: {e}")


def main() -> int:
    """Run all Stripe verification steps."""
    print("\n" + "="*60)
    print("  Bhapi Stripe Integration Verification")
    print("  Test mode only — safe to run repeatedly")
    print("="*60)

    if not preflight_checks():
        return 1

    customer_id = test_customer_creation()
    if not customer_id:
        return 1

    test_checkout_sessions(customer_id)
    test_subscription_lifecycle(customer_id)
    test_portal_session(customer_id)
    test_webhook_events()
    cleanup()

    section("Summary")
    print("  Stripe integration verification complete.")
    print("  Review any [FAIL] items above and address before launch.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
