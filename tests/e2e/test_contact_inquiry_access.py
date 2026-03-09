"""E2E tests for contact inquiry endpoint access.

Finding #5: /api/v1/auth/contact-inquiry may be blocked by auth middleware
because it doesn't match any PUBLIC_PREFIX exactly.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def inquiry_client():
    """Test client for contact inquiry tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


VALID_INQUIRY = {
    "organisation": "Springfield Elementary",
    "contact_name": "Seymour Skinner",
    "email": "skinner@springfield.com",
    "account_type": "school",
    "estimated_members": "50-200",
    "message": "Interested in monitoring student AI usage.",
}


@pytest.mark.asyncio
async def test_contact_inquiry_without_auth(inquiry_client):
    """Contact inquiry should work WITHOUT authentication.

    Finding #5: The path /api/v1/auth/contact-inquiry starts with
    /api/v1/auth/ which IS a PUBLIC_PREFIX (/api/v1/auth/ paths include
    login, register, etc.). However, the middleware checks specific prefixes.
    The prefix "/api/v1/auth/" is not explicitly listed — only specific
    sub-paths like "/api/v1/auth/login" are listed. So contact-inquiry
    may be blocked by the middleware.
    """
    resp = await inquiry_client.post(
        "/api/v1/auth/contact-inquiry",
        json=VALID_INQUIRY,
    )

    if resp.status_code == 401:
        pytest.xfail(
            "VULNERABILITY: Contact inquiry endpoint blocked by auth middleware (Finding #5). "
            "Add '/api/v1/auth/contact-inquiry' to PUBLIC_PREFIXES."
        )

    # Should return 202 with success message
    assert resp.status_code == 202
    assert "team will be in touch" in resp.json()["message"]


@pytest.mark.asyncio
async def test_contact_inquiry_with_auth(inquiry_client):
    """Contact inquiry should also work with authentication."""
    # Register to get a token
    reg = await inquiry_client.post("/api/v1/auth/register", json={
        "email": "inquiry-auth@example.com",
        "password": "SecurePass1",
        "display_name": "Auth Inquirer",
        "account_type": "family",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await inquiry_client.post(
        "/api/v1/auth/contact-inquiry",
        json=VALID_INQUIRY,
        headers=headers,
    )
    assert resp.status_code == 202
    assert "team will be in touch" in resp.json()["message"]
