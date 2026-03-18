"""E2E tests for free tier and feature gating."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def free_tier_client():
    """Test client for free tier endpoints (public, no DB needed)."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_plans_include_free_tier(free_tier_client):
    """GET /billing/plans now includes free tier."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    assert res.status_code == 200
    plans = res.json()["plans"]
    plan_types = [p["plan_type"] for p in plans]
    assert "free" in plan_types


@pytest.mark.asyncio
async def test_free_plan_has_zero_price(free_tier_client):
    """Free plan has $0 pricing."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    free = next(p for p in plans if p["plan_type"] == "free")
    assert free["price_monthly"] == 0
    assert free["price_annual"] == 0


@pytest.mark.asyncio
async def test_free_plan_has_1_member_limit(free_tier_client):
    """Free plan limits to 1 child."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    free = next(p for p in plans if p["plan_type"] == "free")
    assert free["member_limit"] == 1


@pytest.mark.asyncio
async def test_free_plan_has_3_platform_limit(free_tier_client):
    """Free plan limits to 3 platforms."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    free = next(p for p in plans if p["plan_type"] == "free")
    assert free["platform_limit"] == 3


@pytest.mark.asyncio
async def test_bundle_plan_exists(free_tier_client):
    """Bundle plan is available."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    plan_types = [p["plan_type"] for p in plans]
    assert "bundle" in plan_types


@pytest.mark.asyncio
async def test_bundle_plan_pricing(free_tier_client):
    """Bundle plan has correct pricing."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    plans = res.json()["plans"]
    bundle = next(p for p in plans if p["plan_type"] == "bundle")
    assert bundle["price_monthly"] == 14.99
    assert bundle["price_annual"] == 149.99


@pytest.mark.asyncio
async def test_all_plans_have_features_list(free_tier_client):
    """Every plan has a non-empty features list."""
    res = await free_tier_client.get("/api/v1/billing/plans")
    for plan in res.json()["plans"]:
        assert isinstance(plan["features"], list)
        assert len(plan["features"]) > 0
