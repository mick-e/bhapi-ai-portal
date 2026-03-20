"""E2E tests for email verification flow."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def verify_client():
    """Test client for email verification tests."""
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


@pytest.mark.asyncio
async def test_register_sends_verification_email(verify_client):
    """Registration should attempt to send a verification email."""
    with patch("src.auth.router.send_verification_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        resp = await verify_client.post("/api/v1/auth/register", json={
            "email": "verify-send@example.com",
            "password": "SecurePass1",
            "display_name": "Verify Send",
            "account_type": "family",
            "privacy_notice_accepted": True,
        })
        assert resp.status_code == 201

        # Verify send_verification_email was called
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_sets_flag(verify_client):
    """Verification token should set email_verified to true."""
    from uuid import UUID

    from src.auth.service import create_email_verification_token

    # Register
    reg = await verify_client.post("/api/v1/auth/register", json={
        "email": "verify-flag@example.com",
        "password": "SecurePass1",
        "display_name": "Verify Flag",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check unverified
    me = await verify_client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["email_verified"] is False

    # Create and use verification token
    user_id = UUID(me.json()["id"])
    verify_token = create_email_verification_token(user_id)

    resp = await verify_client.post(
        f"/api/v1/auth/verify-email?token={verify_token}",
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "verify-flag@example.com"

    # Check verified
    me_after = await verify_client.get("/api/v1/auth/me", headers=headers)
    assert me_after.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_unverified_email_feature_gating(verify_client):
    """Document whether unverified email limits feature access."""
    reg = await verify_client.post("/api/v1/auth/register", json={
        "email": "unverified@example.com",
        "password": "SecurePass1",
        "display_name": "Unverified",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try accessing features without verifying email
    me = await verify_client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["email_verified"] is False

    # Access groups (should work even without verification)
    groups = await verify_client.get("/api/v1/groups", headers=headers)
    # Document current behavior — is email verification enforced?
    assert groups.status_code in (200, 403)
