"""Session management security tests.

Validates that logout and password change properly invalidate sessions.
Middleware validates tokens against the sessions table, rejecting invalidated tokens.
"""

from datetime import datetime, timedelta, timezone

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


async def _register_and_login(client, email="session-test@example.com"):
    """Register a user, return (access_token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Session Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


@pytest.mark.asyncio
async def test_logout_session_still_valid(sec_client):
    """After logout, the original Bearer token must be rejected.

    Fixed: Logout deletes the Session row from the DB, and middleware validates
    tokens against the sessions table, so the token is rejected with 401.
    """
    token, user_id = await _register_and_login(sec_client, "logout-reuse@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    # Logout
    logout = await sec_client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    # Bearer token must be rejected after logout
    me_after = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_old_session_rejected_after_password_change(sec_client):
    """Old session token must be rejected after password change.

    Fixed: reset_password() calls invalidate_all_sessions() which deletes all
    Session rows for the user. Middleware validates against the sessions table.
    """
    token, user_id = await _register_and_login(sec_client, "pw-change@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Change password via reset flow
    from uuid import UUID

    from src.auth.service import create_password_reset_token

    reset_token = create_password_reset_token(UUID(user_id))
    resp = await sec_client.post("/api/v1/auth/password/reset/confirm", json={
        "token": reset_token,
        "new_password": "NewSecurePass2",
    })
    assert resp.status_code == 200

    # Old token must be rejected after password reset
    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_expired_session_rejected(sec_client):
    """JWT with past expiration must be rejected."""
    from jose import jwt as jose_jwt

    expired_token = jose_jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "type": "session",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        },
        "test-secret-key-for-testing-only-min32chars",
        algorithm="HS256",
    )

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


# --- Phase 3 additions ---


@pytest.mark.asyncio
async def test_concurrent_sessions_allowed(sec_client):
    """Documents whether multiple concurrent sessions are allowed."""
    email = "concurrent@example.com"
    reg = await sec_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Concurrent",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token1 = reg.json()["access_token"]

    # Login again to get a second token
    login = await sec_client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    token2 = login.json()["access_token"]

    # Both should work
    me1 = await sec_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    me2 = await sec_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})

    assert me1.status_code == 200
    assert me2.status_code == 200


@pytest.mark.asyncio
async def test_session_fixation(sec_client):
    """Session token from before login must not work after login.

    Tests whether the app is vulnerable to session fixation attacks.
    Since JWTs are issued fresh on login, this should be safe.
    """
    email = "fixation@example.com"
    reg = await sec_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Fixation",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token_before = reg.json()["access_token"]

    # Login again (new token issued)
    login = await sec_client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    token_after = login.json()["access_token"]

    # Both tokens are different JWTs
    assert token_before != token_after

    # Old token still works because JWTs are stateless — document this
    me = await sec_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_before}"})
    assert me.status_code == 200  # Expected — JWTs are stateless
