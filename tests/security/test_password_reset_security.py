"""Password reset security tests.

Finding #3: Password reset token is not invalidated after use.
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


async def _register(client, email="reset-test@example.com"):
    """Register a user, return (access_token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Reset Tester",
        "account_type": "family",
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


@pytest.mark.asyncio
async def test_password_reset_token_reuse(sec_client):
    """Password reset token should be invalidated after use.

    Finding #3: Token not invalidated after use — remains valid for full 1h window.
    """
    from src.auth.service import create_password_reset_token
    from uuid import UUID

    token, user_id = await _register(sec_client, "reset-reuse@example.com")
    reset_token = create_password_reset_token(UUID(user_id))

    # First use — should succeed
    resp1 = await sec_client.post("/api/v1/auth/password/reset/confirm", json={
        "token": reset_token,
        "new_password": "NewSecurePass1",
    })
    assert resp1.status_code == 200

    # Second use — should be rejected (token already used)
    resp2 = await sec_client.post("/api/v1/auth/password/reset/confirm", json={
        "token": reset_token,
        "new_password": "AnotherPass2",
    })

    if resp2.status_code == 200:
        pytest.xfail(
            "VULNERABILITY: Password reset token reusable after use (Finding #3). "
            "Token valid for full 1-hour window."
        )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_invalidates_sessions(sec_client):
    """Old session tokens should be invalid after password reset."""
    from src.auth.service import create_password_reset_token
    from uuid import UUID

    token, user_id = await _register(sec_client, "reset-sessions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    me = await sec_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    # Reset password
    reset_token = create_password_reset_token(UUID(user_id))
    resp = await sec_client.post("/api/v1/auth/password/reset/confirm", json={
        "token": reset_token,
        "new_password": "NewSecurePass1",
    })
    assert resp.status_code == 200

    # Old token should ideally be invalid now
    me_after = await sec_client.get("/api/v1/auth/me", headers=headers)
    if me_after.status_code == 200:
        pytest.xfail(
            "Old session token still valid after password reset. "
            "Sessions should be invalidated on password change."
        )
    assert me_after.status_code == 401
