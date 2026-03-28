"""Security tests: Health endpoint must not leak DB error details in production."""

import pytest
from unittest.mock import patch, AsyncMock, PropertyMock, MagicMock

from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.mark.asyncio
async def test_health_production_no_db_error_details():
    """In production, /health must not expose database_error details (A2-5)."""
    app = create_app()

    # Simulate a DB connection failure
    mock_conn_cm = AsyncMock()
    mock_conn_cm.__aenter__ = AsyncMock(
        side_effect=ConnectionRefusedError("connection refused to 10.0.0.1:5432")
    )
    mock_conn_cm.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn_cm

    # Patch settings to simulate production AND patch engine for DB failure
    # The patches must be active during the request (not just during create_app)
    with (
        patch("src.main.settings") as mock_settings,
        patch("src.database.engine", mock_engine),
        patch("src.redis_client.is_redis_available", return_value=False),
    ):
        mock_settings.is_production = True
        mock_settings.environment = "production"
        mock_settings.app_version = "0.0.0-test"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/health")

    data = resp.json()
    # Must NOT contain the detailed error string
    assert "database_error" not in data, (
        f"Production health endpoint leaked database_error: {data.get('database_error')}"
    )
    # database field should just say "error"
    assert data.get("database") == "error"
    # status should be degraded
    assert data.get("status") == "degraded"


@pytest.mark.asyncio
async def test_health_development_no_db_error_leak():
    """In development, /health skips DB check so no error details are possible."""
    app = create_app()

    with (
        patch("src.main.settings") as mock_settings,
        patch("src.redis_client.is_redis_available", return_value=False),
    ):
        mock_settings.is_production = False
        mock_settings.environment = "development"
        mock_settings.app_version = "0.0.0-test"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/health")

    data = resp.json()
    assert data.get("status") in ("healthy", "degraded")
    assert "version" in data
