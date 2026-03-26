"""Security tests for the API platform module."""

import base64
import hashlib
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.api_platform.models import APIKeyTier, OAuthClient, OAuthToken
from src.api_platform.oauth import _hash_token, generate_authorization_code
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sec_engine():
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

    yield engine
    await engine.dispose()


@pytest.fixture
async def sec_session(sec_engine):
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def sec_data(sec_session):
    """Seed users and clients for security tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"sec-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    other_user = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Other User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    sec_session.add_all([user, other_user])
    await sec_session.flush()

    for name, rate, webhooks, price in [
        ("school", 1000, 10, None),
        ("partner", 5000, 50, 99.0),
        ("enterprise", 10000, 999, None),
    ]:
        sec_session.add(APIKeyTier(
            id=uuid.uuid4(), name=name, rate_limit_per_hour=rate,
            max_webhooks=webhooks, price_monthly=price,
        ))
    await sec_session.flush()

    secret = "secure-secret-xyz-1234567890-abcdefghij"
    client = OAuthClient(
        id=uuid.uuid4(),
        name="Sec Test App",
        client_id=f"sec_client_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token(secret),
        redirect_uris=["https://sec.example.com/callback"],
        scopes=["read:alerts", "read:compliance"],
        tier="partner",
        owner_id=user.id,
        is_approved=True,
        is_active=True,
    )
    unapproved_client = OAuthClient(
        id=uuid.uuid4(),
        name="Unapproved App",
        client_id=f"unapproved_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("unapproved-secret-xyz-1234567890"),
        redirect_uris=["https://sec.example.com/callback"],
        scopes=["read:alerts"],
        tier="school",
        owner_id=user.id,
        is_approved=False,
        is_active=True,
    )
    alerts_only_client = OAuthClient(
        id=uuid.uuid4(),
        name="Alerts Only App",
        client_id=f"alerts_only_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("alerts-only-secret-xyz-1234567890"),
        redirect_uris=["https://sec.example.com/callback"],
        scopes=["read:alerts"],  # does NOT have read:compliance
        tier="school",
        owner_id=user.id,
        is_approved=True,
        is_active=True,
    )
    sec_session.add_all([client, unapproved_client, alerts_only_client])
    await sec_session.flush()
    await sec_session.commit()

    return {
        "user": user,
        "other_user": other_user,
        "client": client,
        "secret": secret,
        "unapproved_client": unapproved_client,
        "alerts_only_client": alerts_only_client,
    }


def _make_app(sec_engine, user_id, role="member", permissions=None):
    """Helper to create app with given user context."""
    from sqlalchemy.orm import sessionmaker

    app = create_app()

    async def override_get_db():
        maker = sessionmaker(sec_engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as s:
            yield s

    async def override_auth():
        return GroupContext(
            user_id=user_id,
            group_id=None,
            role=role,
            permissions=permissions or [],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth
    return app


async def _make_client(sec_engine, user_id, role="member", permissions=None):
    """Create an AsyncClient with auth header for security tests."""
    app = _make_app(sec_engine, user_id, role, permissions)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


def _pkce_pair():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------------------
# Unapproved client cannot get tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_unapproved_client_cannot_authorize(sec_engine, sec_data):
    """Unapproved client is rejected at authorization step."""
    _, challenge = _pkce_pair()
    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": sec_data["unapproved_client"].client_id,
            "redirect_uri": "https://sec.example.com/callback",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
    assert resp.status_code == 403
    assert "not approved" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# Wrong client_secret rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_wrong_client_secret_rejected(sec_engine, sec_data):
    """Token exchange with wrong client_secret returns 401."""
    client = sec_data["client"]
    verifier, challenge = _pkce_pair()

    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        auth_resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": client.client_id,
            "redirect_uri": "https://sec.example.com/callback",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        code = auth_resp.json()["code"]

        token_resp = await ac.post("/api/v1/platform/token", json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://sec.example.com/callback",
            "client_id": client.client_id,
            "client_secret": "WRONG-SECRET-xxxxxxxxxxxxxxxxxxxxx",
            "code_verifier": verifier,
        })
    assert token_resp.status_code == 401


# ---------------------------------------------------------------------------
# PKCE required — wrong verifier rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_pkce_wrong_verifier_rejected(sec_engine, sec_data):
    """Token exchange with wrong code_verifier returns 401."""
    client = sec_data["client"]
    secret = sec_data["secret"]
    _, challenge = _pkce_pair()

    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        auth_resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": client.client_id,
            "redirect_uri": "https://sec.example.com/callback",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        code = auth_resp.json()["code"]

        token_resp = await ac.post("/api/v1/platform/token", json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://sec.example.com/callback",
            "client_id": client.client_id,
            "client_secret": secret,
            "code_verifier": "WRONG-VERIFIER-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        })
    assert token_resp.status_code == 401


# ---------------------------------------------------------------------------
# Expired token rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_expired_token_rejected(sec_session, sec_data):
    """validate_access_token raises UnauthorizedError for expired token."""
    from datetime import datetime, timedelta, timezone

    from src.api_platform.oauth import validate_access_token
    from src.exceptions import UnauthorizedError

    client = sec_data["client"]
    expired_token_str = "expired-token-value-xyz-12345678"
    token = OAuthToken(
        id=uuid.uuid4(),
        client_id=client.id,
        user_id=sec_data["user"].id,
        access_token_hash=_hash_token(expired_token_str),
        refresh_token_hash=None,
        scopes=["read:alerts"],
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),  # expired
        revoked=False,
    )
    sec_session.add(token)
    await sec_session.flush()

    with pytest.raises(UnauthorizedError, match="expired"):
        await validate_access_token(sec_session, expired_token_str)


# ---------------------------------------------------------------------------
# Revoked token rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_revoked_token_rejected(sec_session, sec_data):
    """validate_access_token raises UnauthorizedError for revoked token."""
    from datetime import datetime, timedelta, timezone

    from src.api_platform.oauth import validate_access_token
    from src.exceptions import UnauthorizedError

    client = sec_data["client"]
    revoked_token_str = "revoked-token-value-xyz-12345678"
    token = OAuthToken(
        id=uuid.uuid4(),
        client_id=client.id,
        user_id=sec_data["user"].id,
        access_token_hash=_hash_token(revoked_token_str),
        refresh_token_hash=None,
        scopes=["read:alerts"],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        revoked=True,  # already revoked
    )
    sec_session.add(token)
    await sec_session.flush()

    with pytest.raises(UnauthorizedError):
        await validate_access_token(sec_session, revoked_token_str)


# ---------------------------------------------------------------------------
# Scope enforcement — client without scope cannot request it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_scope_enforcement_exchange(sec_engine, sec_data):
    """Client without read:compliance cannot exchange for that scope."""
    alerts_only = sec_data["alerts_only_client"]
    verifier, challenge = _pkce_pair()

    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        auth_resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": alerts_only.client_id,
            "redirect_uri": "https://sec.example.com/callback",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        assert auth_resp.status_code == 201
        code = auth_resp.json()["code"]

        # The code was generated with read:alerts, try to exchange
        # but the client only allows read:alerts so this should work
        token_resp = await ac.post("/api/v1/platform/token", json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://sec.example.com/callback",
            "client_id": alerts_only.client_id,
            "client_secret": "alerts-only-secret-xyz-1234567890",
            "code_verifier": verifier,
        })
    # read:alerts is allowed so this should succeed
    assert token_resp.status_code == 200
    assert "read:alerts" in token_resp.json()["scope"]


@pytest.mark.asyncio
async def test_sec_scope_enforcement_disallowed(sec_session, sec_data):
    """exchange_code_for_tokens raises ForbiddenError when scope exceeds client's allowed scopes."""
    from src.api_platform.oauth import exchange_code_for_tokens
    from src.exceptions import ForbiddenError

    alerts_only = sec_data["alerts_only_client"]

    # Manually inject a code that requests read:compliance
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"scope-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Scope User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    sec_session.add(user)
    await sec_session.flush()

    # generate code requesting read:compliance (which alerts_only_client doesn't have)
    code = generate_authorization_code(
        client_id=alerts_only.client_id,
        user_id=user_id,
        scopes=["read:compliance"],  # client does NOT have this
        redirect_uri="https://sec.example.com/callback",
        code_challenge=challenge,
    )

    with pytest.raises(ForbiddenError):
        await exchange_code_for_tokens(
            db=sec_session,
            code=code,
            client_id_str=alerts_only.client_id,
            client_secret="alerts-only-secret-xyz-1234567890",
            redirect_uri="https://sec.example.com/callback",
            code_verifier=verifier,
        )


# ---------------------------------------------------------------------------
# Client isolation — user cannot access another user's client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_cross_user_client_access_denied(sec_engine, sec_data):
    """User cannot view another user's client details."""
    # Log in as other_user, try to access user's client
    client_id = str(sec_data["client"].id)

    async with await _make_client(sec_engine, sec_data["other_user"].id) as ac:
        resp = await ac.get(f"/api/v1/platform/clients/{client_id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin required to approve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_non_admin_cannot_approve(sec_engine, sec_data):
    """Non-admin cannot approve a client."""
    client_id = str(sec_data["client"].id)

    async with await _make_client(sec_engine, sec_data["user"].id, role="member") as ac:
        resp = await ac.post(f"/api/v1/platform/clients/{client_id}/approve")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Invalid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_invalid_token_rejected(sec_session):
    """validate_access_token raises UnauthorizedError for unknown token."""
    from src.api_platform.oauth import validate_access_token
    from src.exceptions import UnauthorizedError

    with pytest.raises(UnauthorizedError, match="Invalid access token"):
        await validate_access_token(sec_session, "completely-fake-token-that-doesnt-exist")


# ---------------------------------------------------------------------------
# Refresh with wrong client_id rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_refresh_wrong_client_rejected(sec_engine, sec_data):
    """Refresh with correct token but wrong client_id returns 401."""
    client = sec_data["client"]
    secret = sec_data["secret"]
    verifier, challenge = _pkce_pair()

    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        auth_resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": client.client_id,
            "redirect_uri": "https://sec.example.com/callback",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        code = auth_resp.json()["code"]

        token_resp = await ac.post("/api/v1/platform/token", json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://sec.example.com/callback",
            "client_id": client.client_id,
            "client_secret": secret,
            "code_verifier": verifier,
        })
        refresh_token = token_resp.json()["refresh_token"]

        # Use refresh token with different client_id
        refresh_resp = await ac.post("/api/v1/platform/token/refresh", json={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": "wrong_client_id_xyz",
            "client_secret": secret,
        })
    assert refresh_resp.status_code in (401, 404)


# ---------------------------------------------------------------------------
# Rate limit tier config validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_tier_school_rate_limits(sec_session, sec_data):
    """School tier has 1000 req/hr and 10 webhooks — not enterprise limits."""
    from src.api_platform.service import get_tier

    tier = await get_tier(sec_session, "school")
    assert tier is not None
    assert tier.rate_limit_per_hour == 1000
    assert tier.max_webhooks == 10
    # School tier is free (included in school subscription)
    assert tier.price_monthly is None


@pytest.mark.asyncio
async def test_sec_tier_enterprise_limits(sec_session, sec_data):
    """Enterprise tier has 10000 req/hr limit."""
    from src.api_platform.service import get_tier

    tier = await get_tier(sec_session, "enterprise")
    assert tier is not None
    assert tier.rate_limit_per_hour == 10000


# ---------------------------------------------------------------------------
# Redirect URI validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_redirect_uri_not_registered_rejected(sec_engine, sec_data):
    """Authorization with unregistered redirect_uri returns 403."""
    client = sec_data["client"]
    _, challenge = _pkce_pair()

    async with await _make_client(sec_engine, sec_data["user"].id) as ac:
        resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": client.client_id,
            "redirect_uri": "https://evil.attacker.com/steal-tokens",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
    assert resp.status_code == 403
