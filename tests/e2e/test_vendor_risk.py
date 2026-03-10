"""E2E tests for vendor risk endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def vendor_client():
    """Test client for vendor risk endpoints."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_get_all_vendor_risks(vendor_client):
    """GET /billing/vendor-risk returns all vendors."""
    res = await vendor_client.get("/api/v1/billing/vendor-risk")
    assert res.status_code == 200
    data = res.json()
    assert "vendors" in data
    assert len(data["vendors"]) == 5


@pytest.mark.asyncio
async def test_get_vendor_risk_openai(vendor_client):
    """GET /billing/vendor-risk/openai returns OpenAI assessment."""
    res = await vendor_client.get("/api/v1/billing/vendor-risk/openai")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "openai"
    assert data["name"] == "OpenAI"
    assert "overall_score" in data
    assert "grade" in data
    assert "category_scores" in data
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_get_vendor_risk_unknown_returns_404(vendor_client):
    """GET /billing/vendor-risk/unknown returns 404."""
    res = await vendor_client.get("/api/v1/billing/vendor-risk/unknown")
    assert res.status_code == 404
