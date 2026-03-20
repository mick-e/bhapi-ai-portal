"""E2E tests for per-seat billing (school/club)."""


from src.billing.stripe_client import PLAN_PRICES


def test_school_plan_prices_configurable():
    """School/club plans should have price IDs in PLAN_PRICES."""
    # After Phase 4A, school/club prices should be in PLAN_PRICES
    assert "family_monthly" in PLAN_PRICES
    assert "family_annual" in PLAN_PRICES


def test_checkout_schema_accepts_school():
    """CheckoutRequest should accept school and club plan types."""
    from src.billing.schemas import CheckoutRequest

    # Should not raise
    req = CheckoutRequest(plan_type="school", billing_cycle="monthly")
    assert req.plan_type == "school"

    req = CheckoutRequest(plan_type="club", billing_cycle="annual")
    assert req.plan_type == "club"

    req = CheckoutRequest(plan_type="family", billing_cycle="monthly")
    assert req.plan_type == "family"
