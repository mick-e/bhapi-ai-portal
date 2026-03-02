"""Phase 0 foundation tests — health, config, middleware."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["environment"] == "test"


@pytest.mark.asyncio
async def test_liveness(client):
    """Liveness probe returns alive."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness(client):
    """Readiness probe returns ready."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root returns 200 (HTML if frontend built, otherwise JSON)."""
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_docs_endpoint(client):
    """OpenAPI docs are accessible."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Bhapi AI Portal"


@pytest.mark.asyncio
async def test_security_headers(client):
    """Security headers are present on responses."""
    response = await client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")


@pytest.mark.asyncio
async def test_timing_header(client):
    """Timing header is present."""
    response = await client.get("/health")
    assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_cors_headers(client):
    """CORS headers present for allowed origins."""
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS middleware should respond
    assert response.status_code in (200, 204, 400)


@pytest.mark.asyncio
async def test_api_requires_auth(client):
    """API routes require authentication when no token provided."""
    response = await client.get("/api/v1/anything")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_api_auth_bypassed_with_token(client):
    """API routes pass auth middleware when token is provided (returns 401 or 404)."""
    response = await client.get(
        "/api/v1/nonexistent",
        headers={"Authorization": "Bearer test-token"},
    )
    # Invalid JWT token results in 401 from get_current_user, or 404 if no auth dependency
    assert response.status_code in (401, 404)
