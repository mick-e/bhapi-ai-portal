"""E2E tests for the billing module — subscriptions, LLM accounts, spend, thresholds.

Covers subscription creation/duplicate detection, LLM account connect/list/disconnect,
spend summary retrieval, and budget threshold management.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="billing@test.com"):
    """Register + login, return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Billing Tester",
        "account_type": "family",
    })
    user_id = reg.json()["id"]
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    return login.json()["access_token"], user_id


async def _create_group(client, headers):
    """Create a group, return group_id."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Billing Family",
        "type": "family",
    }, headers=headers)
    return grp.json()["id"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def billing_client():
    """Test client with committing DB session for billing tests."""
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


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_subscription(billing_client):
    """POST /billing/subscribe creates subscription (201)."""
    token, _ = await _register_and_login(billing_client)
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/subscribe",
        json={
            "group_id": gid,
            "plan_type": "family",
            "billing_cycle": "monthly",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["plan_type"] == "family"
    assert data["billing_cycle"] == "monthly"
    assert data["status"] == "active"
    assert data["group_id"] == gid


@pytest.mark.asyncio
async def test_create_subscription_annual(billing_client):
    """Annual billing cycle works."""
    token, _ = await _register_and_login(billing_client, "annual@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/subscribe",
        json={"group_id": gid, "plan_type": "starter", "billing_cycle": "annual"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["billing_cycle"] == "annual"


@pytest.mark.asyncio
async def test_create_subscription_free_plan(billing_client):
    """Free plan subscription."""
    token, _ = await _register_and_login(billing_client, "free@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/subscribe",
        json={"group_id": gid, "plan_type": "free"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["plan_type"] == "free"


@pytest.mark.asyncio
async def test_duplicate_subscription_returns_409(billing_client):
    """Creating subscription when one exists returns 409."""
    token, _ = await _register_and_login(billing_client, "dup@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    await billing_client.post(
        "/api/v1/billing/subscribe",
        json={"group_id": gid, "plan_type": "family"},
        headers=headers,
    )

    resp = await billing_client.post(
        "/api/v1/billing/subscribe",
        json={"group_id": gid, "plan_type": "starter"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_subscription(billing_client):
    """GET /billing/subscription returns current subscription."""
    token, _ = await _register_and_login(billing_client, "getsub@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    await billing_client.post(
        "/api/v1/billing/subscribe",
        json={"group_id": gid, "plan_type": "school"},
        headers=headers,
    )

    resp = await billing_client.get(
        f"/api/v1/billing/subscription?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["plan_type"] == "school"


@pytest.mark.asyncio
async def test_get_subscription_nonexistent(billing_client):
    """GET subscription for group with none returns 404."""
    token, _ = await _register_and_login(billing_client, "nosub@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.get(
        f"/api/v1/billing/subscription?group_id={gid}", headers=headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# LLM account tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_llm_account(billing_client):
    """POST /billing/llm-accounts connects an account (201)."""
    token, _ = await _register_and_login(billing_client, "llm1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/llm-accounts",
        json={
            "group_id": gid,
            "provider": "openai",
            "api_key": "sk-test-key-12345",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["status"] == "active"
    assert data["group_id"] == gid


@pytest.mark.asyncio
async def test_connect_anthropic_account(billing_client):
    """Connect Anthropic provider."""
    token, _ = await _register_and_login(billing_client, "llm2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/llm-accounts",
        json={"group_id": gid, "provider": "anthropic", "api_key": "sk-ant-test"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_list_llm_accounts(billing_client):
    """GET /billing/llm-accounts lists connected accounts."""
    token, _ = await _register_and_login(billing_client, "llm3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    await billing_client.post(
        "/api/v1/billing/llm-accounts",
        json={"group_id": gid, "provider": "openai", "api_key": "sk-test1"},
        headers=headers,
    )
    await billing_client.post(
        "/api/v1/billing/llm-accounts",
        json={"group_id": gid, "provider": "google", "api_key": "goog-test1"},
        headers=headers,
    )

    resp = await billing_client.get(
        f"/api/v1/billing/llm-accounts?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 2
    providers = {a["provider"] for a in accounts}
    assert "openai" in providers
    assert "google" in providers


@pytest.mark.asyncio
async def test_list_llm_accounts_empty(billing_client):
    """Empty LLM accounts list for new group."""
    token, _ = await _register_and_login(billing_client, "llm4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.get(
        f"/api/v1/billing/llm-accounts?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_disconnect_llm_account(billing_client):
    """DELETE /billing/llm-accounts/{id} deactivates account."""
    token, _ = await _register_and_login(billing_client, "llm5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    create_resp = await billing_client.post(
        "/api/v1/billing/llm-accounts",
        json={"group_id": gid, "provider": "microsoft", "api_key": "ms-test"},
        headers=headers,
    )
    account_id = create_resp.json()["id"]

    resp = await billing_client.delete(
        f"/api/v1/billing/llm-accounts/{account_id}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"


@pytest.mark.asyncio
async def test_disconnect_nonexistent_account(billing_client):
    """DELETE nonexistent LLM account returns 404."""
    token, _ = await _register_and_login(billing_client, "llm6@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await billing_client.delete(
        f"/api/v1/billing/llm-accounts/{uuid4()}", headers=headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Spend summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_spend_summary_empty(billing_client):
    """GET /billing/spend returns zero totals when no records."""
    token, _ = await _register_and_login(billing_client, "spend1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.get(
        f"/api/v1/billing/spend?group_id={gid}"
        "&period_start=2024-01-01T00:00:00Z"
        "&period_end=2024-12-31T23:59:59Z",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_amount"] == 0.0
    assert data["record_count"] == 0
    assert data["currency"] == "USD"


# ---------------------------------------------------------------------------
# Budget thresholds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_budget_threshold(billing_client):
    """POST /billing/thresholds creates threshold (201)."""
    token, _ = await _register_and_login(billing_client, "thresh1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/thresholds",
        json={
            "group_id": gid,
            "type": "soft",
            "amount": 50.0,
            "currency": "USD",
            "notify_at": [50, 80, 100],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "soft"
    assert data["amount"] == 50.0
    assert data["notify_at"] == [50, 80, 100]


@pytest.mark.asyncio
async def test_create_hard_threshold(billing_client):
    """Create hard budget threshold."""
    token, _ = await _register_and_login(billing_client, "thresh2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.post(
        "/api/v1/billing/thresholds",
        json={"group_id": gid, "type": "hard", "amount": 100.0},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "hard"
    assert resp.json()["amount"] == 100.0


@pytest.mark.asyncio
async def test_list_thresholds(billing_client):
    """GET /billing/thresholds lists all thresholds for group."""
    token, _ = await _register_and_login(billing_client, "thresh3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    await billing_client.post(
        "/api/v1/billing/thresholds",
        json={"group_id": gid, "type": "soft", "amount": 25.0},
        headers=headers,
    )
    await billing_client.post(
        "/api/v1/billing/thresholds",
        json={"group_id": gid, "type": "hard", "amount": 100.0},
        headers=headers,
    )

    resp = await billing_client.get(
        f"/api/v1/billing/thresholds?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    thresholds = resp.json()
    assert len(thresholds) == 2
    types = {t["type"] for t in thresholds}
    assert "soft" in types
    assert "hard" in types


@pytest.mark.asyncio
async def test_list_thresholds_empty(billing_client):
    """Empty threshold list for new group."""
    token, _ = await _register_and_login(billing_client, "thresh4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(billing_client, headers)

    resp = await billing_client.get(
        f"/api/v1/billing/thresholds?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_billing_requires_auth(billing_client):
    """Billing endpoints require auth."""
    resp = await billing_client.get(
        f"/api/v1/billing/subscription?group_id={uuid4()}"
    )
    assert resp.status_code == 401
