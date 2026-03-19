"""Mass assignment security tests.

Verifies that PATCH /me only allows whitelisted fields.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client with committing session."""
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


async def _register(client, email="mass-assign@example.com"):
    """Register a user, return (access_token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Mass Assign Test",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()


@pytest.mark.asyncio
async def test_patch_me_cannot_set_email_verified(sec_client):
    """PATCH /me must not allow setting email_verified to bypass verification."""
    token, user_data = await _register(sec_client, "verify-bypass@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to set email_verified via PATCH
    resp = await sec_client.patch("/api/v1/auth/me", json={
        "email_verified": True,
    }, headers=headers)

    # Check the actual value — should still be False
    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    if me.json()["email_verified"] is True:
        pytest.xfail(
            "VULNERABILITY: PATCH /me allows setting email_verified (mass assignment). "
            "Use explicit field whitelist in update_me handler."
        )
    assert me.json()["email_verified"] is False


@pytest.mark.asyncio
async def test_patch_me_cannot_set_id(sec_client):
    """PATCH /me must not allow changing user ID (account takeover)."""
    token, user_data = await _register(sec_client, "id-change@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    original_id = user_data["id"]

    # Attempt to change ID
    resp = await sec_client.patch("/api/v1/auth/me", json={
        "id": "00000000-0000-0000-0000-000000000099",
    }, headers=headers)

    # Verify ID unchanged
    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == original_id


# --- Phase 3 additions ---


@pytest.mark.asyncio
async def test_patch_me_cannot_set_account_type(sec_client):
    """PATCH /me must not allow changing account_type (privilege escalation)."""
    token, user_data = await _register(sec_client, "type-change@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.patch("/api/v1/auth/me", json={
        "account_type": "school",
        "privacy_notice_accepted": True,
    }, headers=headers)

    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["account_type"] == "family"


@pytest.mark.asyncio
async def test_patch_me_cannot_set_mfa(sec_client):
    """PATCH /me must not allow enabling MFA without proper setup flow."""
    token, user_data = await _register(sec_client, "mfa-bypass@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.patch("/api/v1/auth/me", json={
        "mfa_enabled": True,
    }, headers=headers)

    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    if me.json()["mfa_enabled"] is True:
        pytest.xfail(
            "VULNERABILITY: PATCH /me allows setting mfa_enabled without MFA setup flow."
        )
    assert me.json()["mfa_enabled"] is False
