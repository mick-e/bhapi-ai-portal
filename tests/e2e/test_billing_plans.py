"""E2E tests for billing plans endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def plans_client():
    """Test client for plans endpoint (no DB needed — public endpoint)."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_get_plans_returns_all_tiers(plans_client):
    """GET /billing/plans returns all 7 plan tiers.

    Phase 4 added family_plus ($19.99/mo Family+ bundle, Task 21) and
    school_pilot (free 90-day School pilot, Task 20) to the original five.
    """
    res = await plans_client.get("/api/v1/billing/plans")
    assert res.status_code == 200
    data = res.json()
    assert "plans" in data
    plans = data["plans"]
    assert len(plans) == 7
    plan_types = [p["plan_type"] for p in plans]
    for expected in [
        "free",
        "family",
        "bundle",
        "family_plus",
        "school",
        "school_pilot",
        "enterprise",
    ]:
        assert expected in plan_types, f"missing plan: {expected}"


@pytest.mark.asyncio
async def test_family_plan_has_required_fields(plans_client):
    """Family plan has all required fields."""
    res = await plans_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    family = next(p for p in plans if p["plan_type"] == "family")
    assert family["name"] == "Family"
    assert family["price_monthly"] == 9.99
    assert family["price_annual"] == 99.99
    assert family["member_limit"] == 5
    assert isinstance(family["features"], list)
    assert len(family["features"]) > 0


@pytest.mark.asyncio
async def test_school_plan_has_per_seat_pricing(plans_client):
    """School plan has per-seat pricing."""
    res = await plans_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    school = next(p for p in plans if p["plan_type"] == "school")
    assert school["price_unit"] == "per student/month"
    assert school["member_limit"] == 500


@pytest.mark.asyncio
async def test_enterprise_plan_has_custom_pricing(plans_client):
    """Enterprise plan has custom pricing (null prices)."""
    res = await plans_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    enterprise = next(p for p in plans if p["plan_type"] == "enterprise")
    assert enterprise["price_monthly"] is None
    assert enterprise["price_annual"] is None
    assert enterprise["price_unit"] == "custom"
    assert enterprise["member_limit"] is None


@pytest.mark.asyncio
async def test_plans_endpoint_is_public(plans_client):
    """Plans endpoint does not require authentication."""
    # No auth header — should still succeed
    res = await plans_client.get("/api/v1/billing/plans")
    assert res.status_code == 200
