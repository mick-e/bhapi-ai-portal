"""E2E tests for spend sync reliability — retry logic, error tracking, sync status.

Covers GET /billing/sync-status, POST /llm-accounts/{id}/sync (manual trigger),
retry backoff calculation, and error state tracking.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.models import LLMAccount
from src.database import Base, get_db
from src.encryption import encrypt_credential
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, email="sync@example.com"):
    """Register a family user, return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Sync Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group(client, headers):
    """Create a group, return group_id."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Sync Family",
        "type": "family",
    }, headers=headers)
    return grp.json()["id"]


async def _setup_auth(client, email="sync@example.com"):
    """Register, login, create group — return (headers, group_id, user_id)."""
    token, user_id = await _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(client, headers)
    return headers, gid, user_id


async def _connect_llm_account(client, headers, gid, provider="openai", api_key="sk-test-sync"):
    """Connect an LLM account via API, return account_id."""
    resp = await client.post("/api/v1/billing/llm-accounts", json={
        "group_id": gid,
        "provider": provider,
        "api_key": api_key,
    }, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def sync_client():
    """Test client with committing DB session for sync tests."""
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
# Existing Tests (updated for new sync-status response format)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_status_empty(sync_client):
    """GET /billing/sync-status with no LLM accounts returns empty accounts list."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-empty@example.com")

    resp = await client.get(
        f"/api/v1/billing/sync-status?group_id={gid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_accounts"] == 0
    assert data["healthy"] == 0
    assert data["unhealthy"] == 0
    assert data["accounts"] == []


@pytest.mark.asyncio
async def test_sync_status_with_accounts(sync_client):
    """GET /billing/sync-status returns status fields for connected accounts."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-accts@example.com")

    # Connect an LLM account via API
    account_id = await _connect_llm_account(client, headers, gid)

    resp = await client.get(
        f"/api/v1/billing/sync-status?group_id={gid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_accounts"] == 1
    assert data["healthy"] == 1
    assert data["unhealthy"] == 0

    entry = data["accounts"][0]
    assert entry["account_id"] == account_id
    assert entry["provider"] == "openai"
    assert entry["status"] == "healthy"
    assert entry["last_sync_error"] is None
    assert entry["retry_count"] == 0
    assert entry["next_retry_at"] is None


@pytest.mark.asyncio
async def test_sync_status_shows_error(sync_client):
    """GET /billing/sync-status reflects error state on an account."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-err@example.com")

    # Create account directly in DB with error state
    account = LLMAccount(
        id=uuid4(),
        group_id=UUID(gid),
        provider="anthropic",
        credentials_encrypted=encrypt_credential("sk-ant-test"),
        status="active",
        last_error="API key expired",
        last_sync_error="API key expired",
        retry_count=3,
        next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=8),
    )
    session.add(account)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/sync-status?group_id={gid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_accounts"] == 1
    assert data["unhealthy"] == 1

    entry = data["accounts"][0]
    assert entry["provider"] == "anthropic"
    assert entry["last_sync_error"] == "API key expired"
    assert entry["retry_count"] == 3
    assert entry["next_retry_at"] is not None


@pytest.mark.asyncio
async def test_retry_backoff_calculation(sync_client):
    """Verify retry_count increments and next_retry_at uses exponential backoff."""
    client, session = sync_client

    from src.billing.scheduler import sync_all_accounts

    headers, gid, uid = await _setup_auth(client, "sync-backoff@example.com")

    # Create an account with credentials (will fail sync via provider)
    account = LLMAccount(
        id=uuid4(),
        group_id=UUID(gid),
        provider="openai",
        credentials_encrypted=encrypt_credential("sk-bad-key"),
        status="active",
    )
    session.add(account)
    await session.commit()

    # Mock the provider to raise an error
    mock_provider = AsyncMock()
    mock_provider.fetch_usage.side_effect = Exception("Connection timeout")

    with patch("src.billing.scheduler.get_provider", return_value=mock_provider):
        now_before = datetime.now(timezone.utc)
        summary = await sync_all_accounts(session)
        await session.commit()

    assert summary["errored"] == 1

    # Refresh account from DB
    await session.refresh(account)

    assert account.retry_count == 1
    assert account.last_error == "Connection timeout"
    assert account.next_retry_at is not None
    # Backoff for retry_count=1 is 2^1 = 2 minutes
    expected_min = now_before + timedelta(minutes=2)
    # SQLite may return naive datetimes; normalize for comparison
    next_retry = account.next_retry_at
    if next_retry.tzinfo is None:
        next_retry = next_retry.replace(tzinfo=timezone.utc)
    assert next_retry >= expected_min - timedelta(seconds=5)

    # Run again — account should be skipped due to backoff
    with patch("src.billing.scheduler.get_provider", return_value=mock_provider):
        summary2 = await sync_all_accounts(session)
        await session.commit()

    assert summary2["skipped"] == 1
    assert summary2["errored"] == 0

    # Simulate backoff expiry and run again
    account.next_retry_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.commit()

    with patch("src.billing.scheduler.get_provider", return_value=mock_provider):
        summary3 = await sync_all_accounts(session)
        await session.commit()

    await session.refresh(account)
    assert summary3["errored"] == 1
    assert account.retry_count == 2
    # Backoff for retry_count=2 is 2^2 = 4 minutes
    expected_min2 = datetime.now(timezone.utc) + timedelta(minutes=3, seconds=50)
    next_retry2 = account.next_retry_at
    if next_retry2.tzinfo is None:
        next_retry2 = next_retry2.replace(tzinfo=timezone.utc)
    assert next_retry2 >= expected_min2


# ---------------------------------------------------------------------------
# New Tests — manual sync endpoint with retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_sync_success(sync_client):
    """POST /llm-accounts/{id}/sync — connect account, trigger sync, verify success."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-trigger@example.com")

    account_id = await _connect_llm_account(client, headers, gid)

    resp = await client.post(
        f"/api/v1/billing/llm-accounts/{account_id}/sync",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "synced"
    assert data["account_id"] == account_id
    assert data["provider"] == "openai"
    assert data["records_synced"] == 0


@pytest.mark.asyncio
async def test_trigger_sync_no_account(sync_client):
    """POST /llm-accounts/{id}/sync — non-existent account returns 404."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-noexist@example.com")

    fake_id = str(uuid4())
    resp = await client.post(
        f"/api/v1/billing/llm-accounts/{fake_id}/sync",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sync_status_shows_healthy(sync_client):
    """Connect account, get sync status, verify healthy status."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-healthy@example.com")

    account_id = await _connect_llm_account(client, headers, gid)

    resp = await client.get(
        f"/api/v1/billing/sync-status?group_id={gid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_accounts"] == 1
    assert data["healthy"] == 1
    assert data["unhealthy"] == 0

    entry = data["accounts"][0]
    assert entry["account_id"] == account_id
    assert entry["status"] == "healthy"
    assert entry["last_sync_error"] is None
    assert entry["retry_count"] == 0


@pytest.mark.asyncio
async def test_sync_backoff_after_failure(sync_client):
    """Simulate sync failure, verify retry_count increments and next_retry_at is set."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-fail@example.com")

    account_id = await _connect_llm_account(client, headers, gid)

    # Mock spend_sync to raise an error
    with patch(
        "src.billing.spend_sync.sync_provider_spend",
        side_effect=ValueError("Provider API unavailable"),
    ):
        resp = await client.post(
            f"/api/v1/billing/llm-accounts/{account_id}/sync",
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["account_id"] == account_id
    assert data["retry_count"] == 1
    assert "Provider API unavailable" in data["error"]
    assert data["next_retry_at"] is not None

    # Verify sync status shows unhealthy
    status_resp = await client.get(
        f"/api/v1/billing/sync-status?group_id={gid}",
        headers=headers,
    )
    status_data = status_resp.json()
    assert status_data["unhealthy"] == 1
    assert status_data["accounts"][0]["last_sync_error"] is not None
    assert status_data["accounts"][0]["retry_count"] == 1


@pytest.mark.asyncio
async def test_sync_waiting_state(sync_client):
    """Set next_retry_at to future, trigger sync, verify 'waiting' status."""
    client, session = sync_client
    headers, gid, uid = await _setup_auth(client, "sync-wait@example.com")

    # Create account with future next_retry_at directly in DB
    account = LLMAccount(
        id=uuid4(),
        group_id=UUID(gid),
        provider="openai",
        credentials_encrypted=encrypt_credential("sk-test-wait"),
        status="active",
        last_sync_error="Previous error",
        retry_count=2,
        next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    session.add(account)
    await session.commit()

    resp = await client.post(
        f"/api/v1/billing/llm-accounts/{str(account.id)}/sync",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "waiting"
    assert data["account_id"] == str(account.id)
    assert data["retry_count"] == 2
    assert data["next_retry_at"] is not None
