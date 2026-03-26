"""End-to-end tests for the API platform module."""

import base64
import hashlib
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.api_platform.models import APIKeyTier, OAuthClient
from src.api_platform.oauth import _hash_token
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
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


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    """Seed a user, approved client, and tiers."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Partner",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    admin_user = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Admin User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    e2e_session.add_all([user, admin_user])
    await e2e_session.flush()

    # Seed tiers
    for name, rate, webhooks, price in [
        ("school", 1000, 10, None),
        ("partner", 5000, 50, 99.0),
        ("enterprise", 10000, 999, None),
    ]:
        e2e_session.add(APIKeyTier(
            id=uuid.uuid4(), name=name, rate_limit_per_hour=rate,
            max_webhooks=webhooks, price_monthly=price,
        ))
    await e2e_session.flush()

    # Approved client with known secret
    client_secret = "e2e-secret-supersecure-xyz-1234567890"
    client = OAuthClient(
        id=uuid.uuid4(),
        name="E2E Test App",
        client_id=f"e2e_client_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token(client_secret),
        redirect_uris=["https://e2e.example.com/callback"],
        scopes=["read:alerts", "read:activity", "read:compliance"],
        tier="partner",
        owner_id=user.id,
        is_approved=True,
        is_active=True,
    )
    e2e_session.add(client)
    await e2e_session.flush()
    await e2e_session.commit()

    return {
        "user": user,
        "admin_user": admin_user,
        "client": client,
        "client_secret": client_secret,
    }


@pytest_asyncio.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated as the E2E user."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_data["user"].id,
            group_id=None,
            role="member",
            permissions=[],
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac, e2e_data


@pytest_asyncio.fixture
async def e2e_admin_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated as an admin."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_admin_auth():
        return GroupContext(
            user_id=e2e_data["admin_user"].id,
            group_id=None,
            role="admin",
            permissions=["admin"],
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_admin_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac, e2e_data


def _pkce_pair():
    """Generate a PKCE code_verifier + code_challenge pair."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ---------------------------------------------------------------------------
# Client registration E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_register_client(e2e_client):
    """POST /api/v1/platform/clients registers a new client."""
    ac, data = e2e_client
    resp = await ac.post("/api/v1/platform/clients", json={
        "name": "New School App",
        "scopes": ["read:alerts"],
        "tier": "school",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "New School App"
    assert "client_id" in body
    assert "client_secret" in body  # shown only on creation
    assert body["is_approved"] is False


@pytest.mark.asyncio
async def test_e2e_register_client_invalid_scope(e2e_client):
    """Registration with invalid scope returns 422."""
    ac, data = e2e_client
    resp = await ac.post("/api/v1/platform/clients", json={
        "name": "Bad Scope App",
        "scopes": ["write:god_mode"],
        "tier": "school",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_e2e_list_clients(e2e_client):
    """GET /api/v1/platform/clients returns caller's clients."""
    ac, data = e2e_client
    resp = await ac.get("/api/v1/platform/clients")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_e2e_get_client(e2e_client):
    """GET /api/v1/platform/clients/{id} returns client details."""
    ac, data = e2e_client
    client_id = str(data["client"].id)
    resp = await ac.get(f"/api/v1/platform/clients/{client_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == client_id


@pytest.mark.asyncio
async def test_e2e_get_client_not_found(e2e_client):
    """GET /api/v1/platform/clients/{unknown_id} returns 404."""
    ac, data = e2e_client
    resp = await ac.get(f"/api/v1/platform/clients/{uuid.uuid4()}")
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_e2e_approve_client_admin(e2e_admin_client, e2e_engine):
    """Admin can approve a client."""
    ac, data = e2e_admin_client

    # Register a pending client as admin (admin creates for self)
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    pending_client = OAuthClient(
        id=uuid.uuid4(),
        name="Pending Client",
        client_id=f"pending_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("some-secret"),
        scopes=["read:alerts"],
        tier="school",
        owner_id=data["admin_user"].id,
        is_approved=False,
        is_active=True,
    )
    session.add(pending_client)
    await session.commit()
    await session.close()

    resp = await ac.post(f"/api/v1/platform/clients/{pending_client.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["is_approved"] is True


# ---------------------------------------------------------------------------
# OAuth flow E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_oauth_authorize(e2e_client):
    """POST /api/v1/platform/authorize issues authorization code."""
    ac, data = e2e_client
    client = data["client"]
    _, challenge = _pkce_pair()

    resp = await ac.post("/api/v1/platform/authorize", json={
        "client_id": client.client_id,
        "redirect_uri": "https://e2e.example.com/callback",
        "scope": "read:alerts",
        "state": "random-state-string-12345678",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "code" in body
    assert body["state"] == "random-state-string-12345678"


@pytest.mark.asyncio
async def test_e2e_oauth_token_exchange(e2e_client):
    """POST /api/v1/platform/token exchanges code for tokens."""
    ac, data = e2e_client
    client = data["client"]
    secret = data["client_secret"]
    verifier, challenge = _pkce_pair()

    auth_resp = await ac.post("/api/v1/platform/authorize", json={
        "client_id": client.client_id,
        "redirect_uri": "https://e2e.example.com/callback",
        "scope": "read:alerts",
        "state": "state-xyz-12345678",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    assert auth_resp.status_code == 201
    code = auth_resp.json()["code"]

    token_resp = await ac.post("/api/v1/platform/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://e2e.example.com/callback",
        "client_id": client.client_id,
        "client_secret": secret,
        "code_verifier": verifier,
    })
    assert token_resp.status_code == 200
    body = token_resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "Bearer"
    assert "read:alerts" in body["scope"]


@pytest.mark.asyncio
async def test_e2e_oauth_token_refresh(e2e_client):
    """POST /api/v1/platform/token/refresh returns new token pair."""
    ac, data = e2e_client
    client = data["client"]
    secret = data["client_secret"]
    verifier, challenge = _pkce_pair()

    auth_resp = await ac.post("/api/v1/platform/authorize", json={
        "client_id": client.client_id,
        "redirect_uri": "https://e2e.example.com/callback",
        "scope": "read:activity",
        "state": "refresh-state-12345678",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    code = auth_resp.json()["code"]

    token_resp = await ac.post("/api/v1/platform/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://e2e.example.com/callback",
        "client_id": client.client_id,
        "client_secret": secret,
        "code_verifier": verifier,
    })
    assert token_resp.status_code == 200
    refresh_token = token_resp.json()["refresh_token"]

    refresh_resp = await ac.post("/api/v1/platform/token/refresh", json={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client.client_id,
        "client_secret": secret,
    })
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


@pytest.mark.asyncio
async def test_e2e_oauth_token_revoke(e2e_client):
    """POST /api/v1/platform/token/revoke revokes a token."""
    ac, data = e2e_client
    client = data["client"]
    secret = data["client_secret"]
    verifier, challenge = _pkce_pair()

    auth_resp = await ac.post("/api/v1/platform/authorize", json={
        "client_id": client.client_id,
        "redirect_uri": "https://e2e.example.com/callback",
        "scope": "read:alerts",
        "state": "revoke-state-12345678",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    code = auth_resp.json()["code"]

    token_resp = await ac.post("/api/v1/platform/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://e2e.example.com/callback",
        "client_id": client.client_id,
        "client_secret": secret,
        "code_verifier": verifier,
    })
    assert token_resp.status_code == 200
    access_token = token_resp.json()["access_token"]

    revoke_resp = await ac.post("/api/v1/platform/token/revoke", json={
        "token": access_token,
        "client_id": client.client_id,
        "client_secret": secret,
    })
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True


# ---------------------------------------------------------------------------
# Usage tracking E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_get_usage(e2e_client, e2e_engine):
    """GET /api/v1/platform/usage returns usage metrics."""
    from src.api_platform.service import record_usage

    ac, data = e2e_client
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    await record_usage(session, data["client"].id)
    await session.commit()
    await session.close()

    resp = await ac.get(
        "/api/v1/platform/usage",
        params={"client_db_id": str(data["client"].id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_requests" in body
    assert body["total_requests"] >= 1


# ---------------------------------------------------------------------------
# Tier listing E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_list_tiers(e2e_client):
    """GET /api/v1/platform/tiers returns tier configurations."""
    ac, data = e2e_client
    resp = await ac.get("/api/v1/platform/tiers")
    assert resp.status_code == 200
    tiers = resp.json()
    assert isinstance(tiers, list)
    tier_names = {t["name"] for t in tiers}
    assert "school" in tier_names
    assert "partner" in tier_names
    assert "enterprise" in tier_names


@pytest.mark.asyncio
async def test_e2e_approve_non_existent_client(e2e_admin_client):
    """Approving a non-existent client returns 404."""
    ac, data = e2e_admin_client
    fake_id = str(uuid.uuid4())
    resp = await ac.post(f"/api/v1/platform/clients/{fake_id}/approve")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_e2e_authorize_unapproved_client(e2e_engine, e2e_data):
    """Authorizing with an unapproved client returns 403."""
    # Create unapproved client
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    unapproved = OAuthClient(
        id=uuid.uuid4(),
        name="Unapproved App",
        client_id=f"unapproved_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("some-secret"),
        scopes=["read:alerts"],
        tier="school",
        owner_id=e2e_data["user"].id,
        is_approved=False,
        is_active=True,
    )
    session.add(unapproved)
    await session.commit()
    await session.close()

    app = create_app()

    async def override_get_db():
        from sqlalchemy.orm import sessionmaker
        maker = sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as s:
            yield s

    async def override_auth():
        return GroupContext(
            user_id=e2e_data["user"].id,
            group_id=None,
            role="member",
            permissions=[],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth

    _, challenge = _pkce_pair()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        resp = await ac.post("/api/v1/platform/authorize", json={
            "client_id": unapproved.client_id,
            "redirect_uri": "https://example.com/cb",
            "scope": "read:alerts",
            "state": "state-12345678",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_e2e_full_oauth_flow(e2e_client):
    """Full OAuth lifecycle: authorize → exchange → refresh → revoke."""
    ac, data = e2e_client
    client = data["client"]
    secret = data["client_secret"]
    verifier, challenge = _pkce_pair()

    # 1. Authorize
    auth_resp = await ac.post("/api/v1/platform/authorize", json={
        "client_id": client.client_id,
        "redirect_uri": "https://e2e.example.com/callback",
        "scope": "read:alerts read:activity",
        "state": "full-flow-state-12345678",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    assert auth_resp.status_code == 201
    code = auth_resp.json()["code"]

    # 2. Exchange
    token_resp = await ac.post("/api/v1/platform/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "https://e2e.example.com/callback",
        "client_id": client.client_id,
        "client_secret": secret,
        "code_verifier": verifier,
    })
    assert token_resp.status_code == 200
    token_body = token_resp.json()
    token_body["access_token"]
    refresh_token = token_body["refresh_token"]

    # 3. Refresh
    refresh_resp = await ac.post("/api/v1/platform/token/refresh", json={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client.client_id,
        "client_secret": secret,
    })
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]

    # 4. Revoke new access token
    revoke_resp = await ac.post("/api/v1/platform/token/revoke", json={
        "token": new_access,
        "client_id": client.client_id,
        "client_secret": secret,
    })
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True
