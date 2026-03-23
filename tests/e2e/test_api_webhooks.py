"""E2E tests for API platform webhook endpoints and rate limiting."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.api_platform.models import (
    APIKeyTier,
    OAuthClient,
    PlatformWebhookDelivery,
    PlatformWebhookEndpoint,
)
from src.api_platform.oauth import _hash_token
from src.api_platform.webhooks import WEBHOOK_EVENTS
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def wh_e2e_engine():
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
async def wh_e2e_session(wh_e2e_engine):
    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def wh_e2e_data(wh_e2e_session):
    """Seed user, tiers, and an approved OAuth client."""
    user = User(
        id=uuid.uuid4(),
        email=f"wh-e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="WH E2E User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    wh_e2e_session.add(user)
    await wh_e2e_session.flush()

    for name, rate, webhooks, price in [
        ("school", 1000, 10, None),
        ("partner", 5000, 50, 99.0),
        ("enterprise", 10000, 999, None),
    ]:
        wh_e2e_session.add(APIKeyTier(
            id=uuid.uuid4(), name=name, rate_limit_per_hour=rate,
            max_webhooks=webhooks, price_monthly=price,
        ))
    await wh_e2e_session.flush()

    client_secret = "e2e-wh-secret-supersecure-xyz-9876543210"
    client = OAuthClient(
        id=uuid.uuid4(),
        name="WH E2E App",
        client_id=f"wh_e2e_client_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token(client_secret),
        redirect_uris=["https://wh-e2e.example.com/callback"],
        scopes=["read:alerts", "write:webhooks"],
        tier="partner",
        owner_id=user.id,
        is_approved=True,
        is_active=True,
    )
    wh_e2e_session.add(client)
    await wh_e2e_session.flush()
    await wh_e2e_session.commit()

    return {"user": user, "client": client, "client_secret": client_secret}


@pytest_asyncio.fixture
async def wh_e2e_http(wh_e2e_engine, wh_e2e_session, wh_e2e_data):
    """HTTP client authenticated as the E2E webhook user."""
    app = create_app()

    async def get_db_override():
        try:
            yield wh_e2e_session
            await wh_e2e_session.commit()
        except Exception:
            await wh_e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=wh_e2e_data["user"].id,
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
        yield ac, wh_e2e_data


def _mock_http_200():
    """Return a context manager mock for httpx.AsyncClient that always 200s."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.05

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ---------------------------------------------------------------------------
# E2E test 1: Register webhook endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_register_webhook(wh_e2e_http):
    """POST /api/v1/platform/webhooks registers a new webhook endpoint."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    resp = await ac.post(
        "/api/v1/platform/webhooks",
        json={
            "url": "https://myapp.example.com/hooks",
            "events": ["alert.created", "risk_score.changed"],
            "secret": "super-secret-signing-key-16chars",
        },
        params={"client_db_id": client_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["url"] == "https://myapp.example.com/hooks"
    assert "alert.created" in body["events"]
    assert body["is_active"] is True
    assert "id" in body


@pytest.mark.asyncio
async def test_e2e_register_webhook_invalid_event(wh_e2e_http):
    """Registering with an unknown event type returns 422."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    resp = await ac.post(
        "/api/v1/platform/webhooks",
        json={
            "url": "https://myapp.example.com/hooks",
            "events": ["nonexistent.event"],
            "secret": "super-secret-signing-key-16chars",
        },
        params={"client_db_id": client_id},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_e2e_register_webhook_unapproved_client(wh_e2e_engine, wh_e2e_data):
    """Registering a webhook for an unapproved client returns 403."""
    # Create unapproved client
    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    unapproved = OAuthClient(
        id=uuid.uuid4(),
        name="Unapproved WH App",
        client_id=f"unapp_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("secret"),
        scopes=["read:alerts", "write:webhooks"],
        tier="school",
        owner_id=wh_e2e_data["user"].id,
        is_approved=False,
        is_active=True,
    )
    session.add(unapproved)
    await session.commit()
    await session.close()

    app = create_app()
    session2 = AsyncSession(wh_e2e_engine, expire_on_commit=False)

    async def get_db_override():
        yield session2

    async def fake_auth():
        return GroupContext(
            user_id=wh_e2e_data["user"].id,
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
        resp = await ac.post(
            "/api/v1/platform/webhooks",
            json={
                "url": "https://myapp.example.com/hooks",
                "events": ["alert.created"],
                "secret": "super-secret-signing-key-16chars",
            },
            params={"client_db_id": str(unapproved.id)},
        )
    await session2.close()
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# E2E test 2: List webhooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_list_webhooks(wh_e2e_http, wh_e2e_engine, wh_e2e_data):
    """GET /api/v1/platform/webhooks returns registered endpoints."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    # Seed an endpoint directly
    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    ep = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=data["client"].id,
        url="https://list-test.example.com/wh",
        events=["alert.created"],
        secret_hash=_hash_token("list-secret-xyz"),
        is_active=True,
    )
    session.add(ep)
    await session.commit()
    await session.close()

    resp = await ac.get(
        "/api/v1/platform/webhooks",
        params={"client_db_id": client_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1
    urls = [item["url"] for item in body["items"]]
    assert "https://list-test.example.com/wh" in urls


# ---------------------------------------------------------------------------
# E2E test 3: Send test event → check delivery log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_test_webhook_and_delivery_log(wh_e2e_http, wh_e2e_engine, wh_e2e_data):
    """POST /api/v1/platform/webhooks/{id}/test → GET deliveries shows result."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    # Register an endpoint
    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    ep = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=data["client"].id,
        url="https://delivery-test.example.com/wh",
        events=["alert.created"],
        secret_hash=_hash_token("delivery-secret-xyz"),
        is_active=True,
    )
    session.add(ep)
    await session.commit()
    await session.close()

    endpoint_id = str(ep.id)

    # Send test event (mock HTTP delivery)
    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _mock_http_200()
        test_resp = await ac.post(
            f"/api/v1/platform/webhooks/{endpoint_id}/test",
            params={"client_db_id": client_id},
        )

    assert test_resp.status_code == 200, test_resp.text
    test_body = test_resp.json()
    assert test_body["event_type"] == "ping"
    assert test_body["endpoint_id"] == endpoint_id

    # Check delivery log
    log_resp = await ac.get(
        f"/api/v1/platform/webhooks/{endpoint_id}/deliveries",
        params={"client_db_id": client_id},
    )
    assert log_resp.status_code == 200, log_resp.text
    log_body = log_resp.json()
    assert log_body["total"] >= 1
    event_types = [item["event_type"] for item in log_body["items"]]
    assert "ping" in event_types


# ---------------------------------------------------------------------------
# E2E test 4: Delete webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_delete_webhook(wh_e2e_http, wh_e2e_engine, wh_e2e_data):
    """DELETE /api/v1/platform/webhooks/{id} deactivates the endpoint."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    ep = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=data["client"].id,
        url="https://delete-me.example.com/wh",
        events=["checkin.event"],
        secret_hash=_hash_token("delete-secret-xyz"),
        is_active=True,
    )
    session.add(ep)
    await session.commit()
    await session.close()

    endpoint_id = str(ep.id)

    del_resp = await ac.delete(
        f"/api/v1/platform/webhooks/{endpoint_id}",
        params={"client_db_id": client_id},
    )
    assert del_resp.status_code == 204, del_resp.text

    # Endpoint should now appear as inactive in the list
    list_resp = await ac.get(
        "/api/v1/platform/webhooks",
        params={"client_db_id": client_id},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    for item in items:
        if item["id"] == endpoint_id:
            assert item["is_active"] is False


@pytest.mark.asyncio
async def test_e2e_delete_webhook_wrong_owner(wh_e2e_http, wh_e2e_engine, wh_e2e_data):
    """Deleting another client's webhook returns 403."""
    ac, data = wh_e2e_http

    # Create another user first (FK constraint), then client + endpoint
    other_user = User(
        id=uuid.uuid4(),
        email=f"other-wh-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Other WH User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    session = AsyncSession(wh_e2e_engine, expire_on_commit=False)
    session.add(other_user)
    await session.flush()

    other_client = OAuthClient(
        id=uuid.uuid4(),
        name="Other WH App",
        client_id=f"other_wh_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("other-secret"),
        scopes=["read:alerts"],
        tier="school",
        owner_id=other_user.id,
        is_approved=True,
        is_active=True,
    )
    session.add(other_client)
    await session.flush()

    other_ep = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=other_client.id,
        url="https://other-owner.example.com/wh",
        events=["alert.created"],
        secret_hash=_hash_token("other-ep-secret"),
        is_active=True,
    )
    session.add(other_ep)
    await session.commit()
    await session.close()

    # Try to delete other_ep using our client_id — should get 403
    resp = await ac.delete(
        f"/api/v1/platform/webhooks/{other_ep.id}",
        params={"client_db_id": str(data["client"].id)},
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# E2E test 5: Rate limit enforcement via service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_rate_limit_tier_values(wh_e2e_http):
    """GET /api/v1/platform/tiers confirms rate limit values per tier."""
    ac, _ = wh_e2e_http
    resp = await ac.get("/api/v1/platform/tiers")
    assert resp.status_code == 200
    tiers = {t["name"]: t for t in resp.json()}

    assert tiers["school"]["rate_limit_per_hour"] == 1000
    assert tiers["school"]["max_webhooks"] == 10

    assert tiers["partner"]["rate_limit_per_hour"] == 5000
    assert tiers["partner"]["max_webhooks"] == 50

    assert tiers["enterprise"]["rate_limit_per_hour"] == 10000
    assert tiers["enterprise"]["max_webhooks"] == 999


# ---------------------------------------------------------------------------
# E2E test 6: Full webhook lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_webhook_lifecycle(wh_e2e_http, wh_e2e_engine, wh_e2e_data):
    """Register → send test → check deliveries → delete → confirm gone."""
    ac, data = wh_e2e_http
    client_id = str(data["client"].id)

    # 1. Register
    reg_resp = await ac.post(
        "/api/v1/platform/webhooks",
        json={
            "url": "https://lifecycle.example.com/hooks",
            "events": ["alert.created"],
            "secret": "lifecycle-secret-xyz-abcdef1234",
        },
        params={"client_db_id": client_id},
    )
    assert reg_resp.status_code == 201, reg_resp.text
    endpoint_id = reg_resp.json()["id"]

    # 2. Send test event
    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _mock_http_200()
        test_resp = await ac.post(
            f"/api/v1/platform/webhooks/{endpoint_id}/test",
            params={"client_db_id": client_id},
        )
    assert test_resp.status_code == 200

    # 3. Check delivery log
    log_resp = await ac.get(
        f"/api/v1/platform/webhooks/{endpoint_id}/deliveries",
        params={"client_db_id": client_id},
    )
    assert log_resp.status_code == 200
    assert log_resp.json()["total"] >= 1

    # 4. Delete
    del_resp = await ac.delete(
        f"/api/v1/platform/webhooks/{endpoint_id}",
        params={"client_db_id": client_id},
    )
    assert del_resp.status_code == 204

    # 5. Confirm inactive in list
    list_resp = await ac.get(
        "/api/v1/platform/webhooks",
        params={"client_db_id": client_id},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    for item in items:
        if item["id"] == endpoint_id:
            assert item["is_active"] is False
