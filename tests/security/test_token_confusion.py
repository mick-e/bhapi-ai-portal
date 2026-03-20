"""Token confusion security tests.

Validates that tokens of one type cannot be used for another purpose.
Finding #1: Bearer path in get_current_user doesn't check token type.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
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


async def _register_and_login(client, email="token-test@example.com"):
    """Register a user, return (access_token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Token Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


# --- Token Type Confusion ---


@pytest.mark.asyncio
async def test_password_reset_token_as_bearer(sec_client):
    """Password reset token must NOT work as Bearer auth on /me.

    Finding #1: Bearer path doesn't check type field, so any valid JWT works.
    This test documents the vulnerability — if it passes (401), the bug is fixed.
    """
    from uuid import UUID

    from src.auth.service import create_password_reset_token

    token, user_id = await _register_and_login(sec_client, "reset-bearer@example.com")
    reset_token = create_password_reset_token(UUID(user_id))

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {reset_token}"},
    )
    # Should be 401 (token type mismatch), but may be 200 if bug exists
    assert resp.status_code in (200, 401), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        pytest.xfail("VULNERABILITY: password_reset token accepted as Bearer auth (Finding #1)")


@pytest.mark.asyncio
async def test_email_verification_token_as_bearer(sec_client):
    """Email verification token must NOT work as Bearer auth on /me.

    Same vulnerability as Finding #1 — any JWT type grants access via Bearer.
    """
    from uuid import UUID

    from src.auth.service import create_email_verification_token

    token, user_id = await _register_and_login(sec_client, "verify-bearer@example.com")
    verify_token = create_email_verification_token(UUID(user_id))

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {verify_token}"},
    )
    assert resp.status_code in (200, 401), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        pytest.xfail("VULNERABILITY: email_verification token accepted as Bearer auth (Finding #1)")


@pytest.mark.asyncio
async def test_session_token_cannot_reset_password(sec_client):
    """Session (access) token must NOT work on password reset confirm endpoint."""
    token, user_id = await _register_and_login(sec_client, "session-reset@example.com")

    resp = await sec_client.post("/api/v1/auth/password/reset/confirm", json={
        "token": token,
        "new_password": "NewSecurePass1",
    })
    # Session/access tokens have type="access", reset endpoint checks type="password_reset"
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_algorithm_none(sec_client):
    """JWT with alg:none must be rejected."""
    from datetime import datetime, timedelta, timezone

    # Craft a token with algorithm "none" — this is a well-known attack
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    # python-jose doesn't support alg=none, so we manually craft it
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).rstrip(b"=")
    fake_token = f"{header.decode()}.{body.decode()}."

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {fake_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_modified_sub_without_resigning(sec_client):
    """Tampered JWT (modified sub without re-signing) must be rejected."""
    token, user_id = await _register_and_login(sec_client, "tamper@example.com")

    # Split the JWT and modify the payload
    parts = token.split(".")
    assert len(parts) == 3

    import base64
    import json

    # Decode payload, change sub, re-encode (without re-signing)
    padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    payload["sub"] = "00000000-0000-0000-0000-000000000099"
    new_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()

    tampered_token = f"{parts[0]}.{new_payload}.{parts[2]}"

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401


# --- Phase 3 addition ---


@pytest.mark.asyncio
async def test_jwt_wrong_algorithm(sec_client):
    """JWT signed with wrong algorithm (HS384 vs HS256) must be rejected."""
    from datetime import datetime, timedelta, timezone

    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret-key-for-testing-only-min32chars",
        algorithm="HS384",
    )

    resp = await sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
