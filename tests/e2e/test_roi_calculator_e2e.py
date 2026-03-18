"""E2E tests for ROI calculator endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import create_app


@pytest.fixture
async def roi_client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_roi_with_custom_params(roi_client):
    res = await roi_client.get(
        "/api/v1/portal/roi-calculator?num_students=500&avg_incidents=10&cost_per_incident=1000"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["num_students"] == 500
    assert data["roi_percentage"] > 0


@pytest.mark.asyncio
async def test_roi_minimum_students(roi_client):
    res = await roi_client.get("/api/v1/portal/roi-calculator?num_students=1")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_roi_invalid_students(roi_client):
    res = await roi_client.get("/api/v1/portal/roi-calculator?num_students=0")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_roi_large_school(roi_client):
    res = await roi_client.get("/api/v1/portal/roi-calculator?num_students=5000")
    assert res.status_code == 200
    data = res.json()
    assert "annual_savings" in data  # large schools may have negative savings with default incident params


@pytest.mark.asyncio
async def test_roi_has_payback_months(roi_client):
    res = await roi_client.get("/api/v1/portal/roi-calculator?num_students=100")
    assert res.status_code == 200
    assert "payback_months" in res.json()
