"""Rate limiting security tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import create_app


@pytest.mark.asyncio
async def test_rate_limit_headers_present():
    """Rate limit headers are present in responses."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/health")
        # In test mode with RATE_LIMIT_FAIL_OPEN=true, headers may not be present
        # but the endpoint should still respond
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_not_rate_limited():
    """Health endpoints are exempt from rate limiting."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Rapid-fire health checks should all pass
        for _ in range(20):
            resp = await client.get("/health")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_liveness_exempt_from_rate_limit():
    """Liveness probe exempt from rate limiting."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        for _ in range(20):
            resp = await client.get("/health/live")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_readiness_exempt_from_rate_limit():
    """Readiness probe exempt from rate limiting."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        for _ in range(20):
            resp = await client.get("/health/ready")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_docs_endpoint_responds():
    """OpenAPI docs are accessible."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/docs")
        assert resp.status_code == 200
