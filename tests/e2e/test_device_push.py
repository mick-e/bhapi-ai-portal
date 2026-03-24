"""End-to-end tests for push token registration endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def push_engine():
    """Create an in-memory SQLite engine for push token E2E tests."""
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
async def push_session(push_engine):
    """Create a test session for push token tests."""
    session = AsyncSession(push_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def push_user(push_session):
    """Create a test user for push token tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"push-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Push Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    push_session.add(user)

    group = Group(
        id=uuid.uuid4(),
        name="Push Test Family",
        type="family",
        owner_id=user.id,
    )
    push_session.add(group)
    await push_session.flush()

    return {"user": user, "group": group}


@pytest.fixture
async def push_client(push_engine, push_session, push_user):
    """HTTP client authenticated as the push test user."""
    app = create_app()

    async def get_db_override():
        try:
            yield push_session
            await push_session.commit()
        except Exception:
            await push_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=push_user["user"].id,
            group_id=push_user["group"].id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# POST /api/v1/device/push-token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_valid_push_token(push_client):
    """POST /push-token with valid Expo token returns 201."""
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "device_type": "ios",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"] == "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
    assert body["device_type"] == "ios"
    assert body["registered"] is True


@pytest.mark.asyncio
async def test_register_push_token_invalid_format(push_client):
    """POST /push-token with invalid token format returns 422."""
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "InvalidTokenFormat",
        "device_type": "ios",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_push_token_invalid_device_type(push_client):
    """POST /push-token with invalid device_type returns 422."""
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "device_type": "windows",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_push_token_android(push_client):
    """POST /push-token with android device_type returns 201."""
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[android-token-12345]",
        "device_type": "android",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_type"] == "android"
    assert body["registered"] is True


# ---------------------------------------------------------------------------
# GET /api/v1/device/push-tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_push_tokens_returns_registered(push_client):
    """GET /push-tokens returns tokens that were registered."""
    # Register a token first
    await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[list-test-token-abc]",
        "device_type": "ios",
    })

    resp = await push_client.get("/api/v1/device/push-tokens")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1
    tokens = [item["token"] for item in body["items"]]
    assert "ExponentPushToken[list-test-token-abc]" in tokens


@pytest.mark.asyncio
async def test_list_push_tokens_empty(push_client):
    """GET /push-tokens returns empty list when no tokens registered."""
    resp = await push_client.get("/api/v1/device/push-tokens")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# DELETE /api/v1/device/push-token/{token}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unregister_push_token(push_client):
    """DELETE /push-token/{token} removes token and returns 204."""
    token = "ExponentPushToken[delete-me-token-xyz]"

    # Register first
    reg_resp = await push_client.post("/api/v1/device/push-token", json={
        "token": token,
        "device_type": "android",
    })
    assert reg_resp.status_code == 201

    # Unregister
    del_resp = await push_client.delete(
        f"/api/v1/device/push-token/{token}"
    )
    assert del_resp.status_code == 204

    # Confirm it's gone
    list_resp = await push_client.get("/api/v1/device/push-tokens")
    body = list_resp.json()
    tokens = [item["token"] for item in body["items"]]
    assert token not in tokens


@pytest.mark.asyncio
async def test_unregister_nonexistent_token(push_client):
    """DELETE /push-token/{token} for non-existent token returns 204."""
    resp = await push_client.delete(
        "/api/v1/device/push-token/ExponentPushToken[does-not-exist]"
    )
    # Idempotent — not found is still success (no error raised)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_same_token_twice_is_idempotent(push_client):
    """Registering the same token twice upserts and returns 201 both times."""
    token = "ExponentPushToken[upsert-test-token]"

    # First registration
    resp1 = await push_client.post("/api/v1/device/push-token", json={
        "token": token,
        "device_type": "ios",
    })
    assert resp1.status_code == 201

    # Second registration (same token, same device type)
    resp2 = await push_client.post("/api/v1/device/push-token", json={
        "token": token,
        "device_type": "ios",
    })
    assert resp2.status_code == 201
    assert resp2.json()["registered"] is True

    # Only one token should be in the list
    list_resp = await push_client.get("/api/v1/device/push-tokens")
    body = list_resp.json()
    matching = [item for item in body["items"] if item["token"] == token]
    assert len(matching) == 1
