"""Security tests for CSP and HSTS headers.

Covers R-09 (Phase 4 Task 1):
- script-src must NOT include 'unsafe-inline' (XSS defense)
- HSTS must include 'preload' directive (HSTS preload list eligibility)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create a test HTTP client with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_csp_script_src_has_no_unsafe_inline(client):
    """script-src must NOT allow 'unsafe-inline' (XSS protection)."""
    response = await client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")
    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" not in script_src, (
        f"script-src still allows unsafe-inline: {script_src}"
    )


@pytest.mark.asyncio
async def test_hsts_includes_preload(client):
    """HSTS header should include 'preload' directive for HSTS preload list eligibility."""
    response = await client.get("/health/live")
    hsts = response.headers.get("Strict-Transport-Security", "")
    assert "preload" in hsts, f"HSTS missing preload: {hsts}"
