"""E2E tests for extension pairing (setup code creation and exchange).

Covers code creation, successful pairing, expired/used/invalid code rejection,
and verifying the /pair endpoint does not require authentication.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.capture.models import SetupCode
from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def pairing_client():
    """Test client with committing DB session for pairing tests."""
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
        yield client, session

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _setup_auth_with_member(client):
    """Register a user, create a group + member, return (headers, group_id, member_id, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "pairing-user@example.com",
        "password": "SecurePass1",
        "display_name": "Pairing Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert reg.status_code == 201 or reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]

    grp = await client.post("/api/v1/groups", json={
        "name": "Pairing Family",
        "type": "family",
    }, headers=headers)
    assert grp.status_code in (200, 201), grp.text
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    assert mem.status_code in (200, 201), mem.text
    member_id = mem.json()["id"]

    return headers, group_id, member_id, user_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_setup_code(pairing_client):
    """Creating a setup code returns an 8-char hex code expiring ~15 min from now."""
    client, session = pairing_client
    headers, group_id, member_id, _ = await _setup_auth_with_member(client)

    resp = await client.post("/api/v1/capture/setup-codes", json={
        "group_id": group_id,
        "member_id": member_id,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    # 8 hex chars
    assert len(data["code"]) == 8
    assert all(c in "0123456789abcdef" for c in data["code"])

    # Expires roughly 15 minutes from now (allow 60s tolerance)
    expires = datetime.fromisoformat(data["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    expected = datetime.now(timezone.utc) + timedelta(minutes=15)
    assert abs((expires - expected).total_seconds()) < 60


@pytest.mark.asyncio
async def test_exchange_setup_code(pairing_client):
    """Exchanging a valid setup code returns group_id, member_id, and signing_secret."""
    client, session = pairing_client
    headers, group_id, member_id, _ = await _setup_auth_with_member(client)

    # Create a setup code
    create_resp = await client.post("/api/v1/capture/setup-codes", json={
        "group_id": group_id,
        "member_id": member_id,
    }, headers=headers)
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # Exchange it
    pair_resp = await client.post("/api/v1/capture/pair", json={
        "setup_code": code,
    })
    assert pair_resp.status_code == 200, pair_resp.text
    data = pair_resp.json()

    assert data["group_id"] == group_id
    assert data["member_id"] == member_id
    assert len(data["signing_secret"]) > 20  # urlsafe base64, ~43 chars


@pytest.mark.asyncio
async def test_expired_code_rejected(pairing_client):
    """An expired setup code is rejected with 401."""
    client, session = pairing_client
    headers, group_id, member_id, _ = await _setup_auth_with_member(client)

    # Create a setup code
    create_resp = await client.post("/api/v1/capture/setup-codes", json={
        "group_id": group_id,
        "member_id": member_id,
    }, headers=headers)
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # Manually expire the code in the DB
    result = await session.execute(select(SetupCode).where(SetupCode.code == code))
    setup = result.scalar_one()
    setup.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.commit()

    # Try to exchange
    pair_resp = await client.post("/api/v1/capture/pair", json={
        "setup_code": code,
    })
    assert pair_resp.status_code == 401, pair_resp.text


@pytest.mark.asyncio
async def test_used_code_rejected(pairing_client):
    """A setup code that has already been used is rejected with 401."""
    client, session = pairing_client
    headers, group_id, member_id, _ = await _setup_auth_with_member(client)

    # Create a setup code
    create_resp = await client.post("/api/v1/capture/setup-codes", json={
        "group_id": group_id,
        "member_id": member_id,
    }, headers=headers)
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # First exchange succeeds
    pair_resp = await client.post("/api/v1/capture/pair", json={
        "setup_code": code,
    })
    assert pair_resp.status_code == 200

    # Second exchange fails
    pair_resp2 = await client.post("/api/v1/capture/pair", json={
        "setup_code": code,
    })
    assert pair_resp2.status_code == 401, pair_resp2.text


@pytest.mark.asyncio
async def test_invalid_code_rejected(pairing_client):
    """A bogus setup code is rejected with 404."""
    client, session = pairing_client

    pair_resp = await client.post("/api/v1/capture/pair", json={
        "setup_code": "00000000",
    })
    assert pair_resp.status_code == 404, pair_resp.text


@pytest.mark.asyncio
async def test_pair_endpoint_no_auth_required(pairing_client):
    """POST /api/v1/capture/pair does not require auth (no 401 from middleware)."""
    client, session = pairing_client

    # Send request without any auth headers — should not get 401 from middleware
    # (will get 404 because the code doesn't exist, but that's fine)
    pair_resp = await client.post("/api/v1/capture/pair", json={
        "setup_code": "deadbeef",
    })
    # Should be 404 (code not found), NOT 401 (auth required)
    assert pair_resp.status_code == 404, (
        f"Expected 404 for missing code, got {pair_resp.status_code}: {pair_resp.text}"
    )
