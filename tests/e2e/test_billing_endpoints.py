"""E2E tests for billing endpoints — checkout, portal, spend, spend/records, revoke.

Covers POST /checkout, GET /portal (with mocked Stripe), GET /spend (empty + with data),
GET /spend/records (pagination + filters), and POST /llm-accounts/{id}/revoke.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.models import BudgetThreshold, SpendRecord, Subscription
from src.database import Base, get_db
from src.groups.models import GroupMember
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, email="billing-ep@example.com"):
    """Register a family user, return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Billing Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group(client, headers):
    """Create a group, return group_id."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Billing Family",
        "type": "family",
    }, headers=headers)
    return grp.json()["id"]


async def _setup_auth(client, email="billing-ep@example.com"):
    """Register, login, create group — return (headers, group_id, user_id)."""
    token, user_id = await _register_and_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(client, headers)
    return headers, gid, user_id


async def _connect_llm_account(client, headers, gid, provider="openai", api_key="sk-test-key"):
    """Connect an LLM account, return account_id."""
    resp = await client.post("/api/v1/billing/llm-accounts", json={
        "group_id": gid,
        "provider": provider,
        "api_key": api_key,
    }, headers=headers)
    return resp.json()["id"]


async def _create_spend_record(session, group_id, llm_account_id, amount, member_id=None,
                                model=None, token_count=None, hours_ago=0):
    """Insert a SpendRecord directly into the DB."""
    now = datetime.now(timezone.utc)
    record = SpendRecord(
        id=uuid4(),
        group_id=group_id,
        llm_account_id=llm_account_id,
        member_id=member_id,
        period_start=now - timedelta(hours=hours_ago),
        period_end=now - timedelta(hours=max(hours_ago - 1, 0)),
        amount=amount,
        currency="USD",
        token_count=token_count,
        model=model,
    )
    session.add(record)
    await session.flush()
    return record


# ---------------------------------------------------------------------------
# Fixture (matches test_spend_tracking.py pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
async def billing_client():
    """Test client with committing DB session for billing endpoint tests."""
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
# POST /billing/checkout — Stripe Checkout Session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkout_creates_session(billing_client):
    """POST /billing/checkout returns session_id and url when Stripe succeeds."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "checkout1@example.com")

    mock_session = MagicMock()
    mock_session.id = "cs_test_abc123"
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"

    with patch("src.billing.stripe_client._get_stripe") as mock_stripe:
        stripe_mod = MagicMock()
        stripe_mod.Customer.list.return_value = MagicMock(data=[MagicMock(id="cus_test123")])
        stripe_mod.checkout.Session.create.return_value = mock_session
        stripe_mod.StripeError = Exception
        mock_stripe.return_value = stripe_mod

        resp = await client.post("/api/v1/billing/checkout", json={
            "plan_type": "family",
            "billing_cycle": "monthly",
        }, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "cs_test_abc123"
    assert "checkout.stripe.com" in data["url"]


@pytest.mark.asyncio
async def test_checkout_annual_billing(billing_client):
    """POST /billing/checkout with annual billing cycle succeeds."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "checkout2@example.com")

    mock_session = MagicMock()
    mock_session.id = "cs_test_annual"
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_annual"

    with patch("src.billing.stripe_client._get_stripe") as mock_stripe:
        stripe_mod = MagicMock()
        stripe_mod.Customer.list.return_value = MagicMock(data=[MagicMock(id="cus_annual")])
        stripe_mod.checkout.Session.create.return_value = mock_session
        stripe_mod.StripeError = Exception
        mock_stripe.return_value = stripe_mod

        resp = await client.post("/api/v1/billing/checkout", json={
            "plan_type": "family",
            "billing_cycle": "annual",
        }, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["session_id"] == "cs_test_annual"


@pytest.mark.asyncio
async def test_checkout_invalid_plan_type(billing_client):
    """POST /billing/checkout with invalid plan_type returns 422."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "checkout3@example.com")

    resp = await client.post("/api/v1/billing/checkout", json={
        "plan_type": "enterprise",
        "billing_cycle": "monthly",
    }, headers=headers)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_checkout_requires_auth(billing_client):
    """POST /billing/checkout without auth returns 401."""
    client, session = billing_client

    resp = await client.post("/api/v1/billing/checkout", json={
        "plan_type": "family",
        "billing_cycle": "monthly",
    })

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /billing/portal — Stripe Billing Portal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portal_returns_url(billing_client):
    """GET /billing/portal returns portal URL when subscription has stripe_customer_id."""
    client, session = billing_client
    token, user_id = await _register_and_login(client, "portal1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Get the auto-created group from registration (auth resolves this group)
    me = await client.get("/api/v1/auth/me", headers=headers)
    auth_gid = me.json().get("group_id")

    from uuid import UUID
    # Create a subscription with stripe_customer_id on the auth group
    sub = Subscription(
        id=uuid4(),
        group_id=UUID(auth_gid),
        plan_type="family",
        billing_cycle="monthly",
        status="active",
        stripe_customer_id="cus_portal_test",
        stripe_subscription_id="sub_portal_test",
    )
    session.add(sub)
    await session.commit()

    with patch("src.billing.stripe_client._get_stripe") as mock_stripe:
        stripe_mod = MagicMock()
        portal_session = MagicMock()
        portal_session.url = "https://billing.stripe.com/p/session/test_portal"
        stripe_mod.billing_portal.Session.create.return_value = portal_session
        stripe_mod.StripeError = Exception
        mock_stripe.return_value = stripe_mod

        resp = await client.get("/api/v1/billing/portal", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://billing.stripe.com/p/session/test_portal"


@pytest.mark.asyncio
async def test_portal_no_subscription_returns_404(billing_client):
    """GET /billing/portal without a Stripe subscription returns 404."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "portal2@example.com")

    resp = await client.get("/api/v1/billing/portal", headers=headers)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_portal_requires_auth(billing_client):
    """GET /billing/portal without auth returns 401."""
    client, session = billing_client

    resp = await client.get("/api/v1/billing/portal")

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /billing/spend — Spend Summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spend_empty_group(billing_client):
    """GET /billing/spend with no records returns zero totals."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "spend1@example.com")

    resp = await client.get(
        f"/api/v1/billing/spend?group_id={gid}&period=month", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == 0.0
    assert data["budget_usd"] == 0.0
    assert data["budget_remaining_usd"] == 0.0
    assert data["budget_used_percentage"] == 0.0
    assert data["active_spenders"] == 0
    assert data["over_budget_count"] == 0
    assert data["member_breakdown"] == []
    assert data["provider_breakdown"] == []
    assert data["records"] == []
    assert data["period"] == "month"
    assert data["period_label"] == "This Month"


@pytest.mark.asyncio
async def test_spend_with_records(billing_client):
    """GET /billing/spend aggregates spend records correctly."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "spend2@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    # Connect an LLM account
    account_id = await _connect_llm_account(client, headers, gid)
    account_uuid = UUID(account_id)

    # Add a group member
    member = GroupMember(
        id=uuid4(),
        group_id=gid_uuid,
        display_name="Child One",
        role="member",
    )
    session.add(member)
    await session.flush()

    # Create spend records
    await _create_spend_record(session, gid_uuid, account_uuid, 5.50,
                                member_id=member.id, model="gpt-4", token_count=1000, hours_ago=1)
    await _create_spend_record(session, gid_uuid, account_uuid, 3.25,
                                member_id=member.id, model="gpt-4", token_count=500, hours_ago=2)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/spend?group_id={gid}&period=month", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_usd"] == 8.75
    assert data["active_spenders"] == 1
    assert len(data["records"]) == 2


@pytest.mark.asyncio
async def test_spend_day_period(billing_client):
    """GET /billing/spend with period=day filters correctly."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "spend3@example.com")

    resp = await client.get(
        f"/api/v1/billing/spend?group_id={gid}&period=day", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "day"
    assert data["period_label"] == "Today"


@pytest.mark.asyncio
async def test_spend_week_period(billing_client):
    """GET /billing/spend with period=week returns correct label."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "spend4@example.com")

    resp = await client.get(
        f"/api/v1/billing/spend?group_id={gid}&period=week", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "week"
    assert data["period_label"] == "This Week"


@pytest.mark.asyncio
async def test_spend_with_budget_threshold(billing_client):
    """GET /billing/spend reflects budget threshold when set."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "spend5@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    # Create a group-level budget threshold
    threshold = BudgetThreshold(
        id=uuid4(),
        group_id=gid_uuid,
        member_id=None,
        type="soft",
        amount=100.0,
        currency="USD",
        notify_at=[50, 80, 100],
    )
    session.add(threshold)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/spend?group_id={gid}&period=month", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["budget_usd"] == 100.0
    assert data["budget_remaining_usd"] == 100.0
    assert data["budget_used_percentage"] == 0.0


# ---------------------------------------------------------------------------
# GET /billing/spend/records — Paginated Spend Records
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spend_records_empty(billing_client):
    """GET /billing/spend/records with no data returns empty paginated response."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "records1@example.com")

    resp = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["total_pages"] == 1


@pytest.mark.asyncio
async def test_spend_records_pagination(billing_client):
    """GET /billing/spend/records paginates correctly."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "records2@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    account_id = await _connect_llm_account(client, headers, gid)
    account_uuid = UUID(account_id)

    # Create 5 spend records
    for i in range(5):
        await _create_spend_record(session, gid_uuid, account_uuid, 1.0 + i,
                                    model="gpt-4", hours_ago=i)
    await session.commit()

    # Page 1, page_size=2
    resp = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}&page=1&page_size=2", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3

    # Page 3 (last page with 1 item)
    resp2 = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}&page=3&page_size=2", headers=headers
    )
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["page"] == 3


@pytest.mark.asyncio
async def test_spend_records_filter_by_member(billing_client):
    """GET /billing/spend/records filters by member_id."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "records3@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    account_id = await _connect_llm_account(client, headers, gid)
    account_uuid = UUID(account_id)

    member1 = GroupMember(id=uuid4(), group_id=gid_uuid, display_name="Kid A", role="member")
    member2 = GroupMember(id=uuid4(), group_id=gid_uuid, display_name="Kid B", role="member")
    session.add_all([member1, member2])
    await session.flush()

    # 3 records for member1, 1 for member2
    for i in range(3):
        await _create_spend_record(session, gid_uuid, account_uuid, 2.0,
                                    member_id=member1.id, hours_ago=i)
    await _create_spend_record(session, gid_uuid, account_uuid, 5.0,
                                member_id=member2.id, hours_ago=0)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}&member_id={member1.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(item["member_id"] == str(member1.id) for item in data["items"])


@pytest.mark.asyncio
async def test_spend_records_filter_by_provider(billing_client):
    """GET /billing/spend/records filters by provider name."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "records4@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    openai_id = await _connect_llm_account(client, headers, gid, "openai", "sk-openai")
    anthropic_id = await _connect_llm_account(client, headers, gid, "anthropic", "sk-ant")

    openai_uuid = UUID(openai_id)
    anthropic_uuid = UUID(anthropic_id)

    # 2 records for openai, 1 for anthropic
    await _create_spend_record(session, gid_uuid, openai_uuid, 3.0, hours_ago=1)
    await _create_spend_record(session, gid_uuid, openai_uuid, 4.0, hours_ago=2)
    await _create_spend_record(session, gid_uuid, anthropic_uuid, 7.0, hours_ago=0)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}&provider=openai",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_spend_records_response_shape(billing_client):
    """GET /billing/spend/records items have expected fields."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "records5@example.com")

    from uuid import UUID
    gid_uuid = UUID(gid)

    account_id = await _connect_llm_account(client, headers, gid)
    account_uuid = UUID(account_id)

    await _create_spend_record(session, gid_uuid, account_uuid, 2.50,
                                model="gpt-4o", token_count=750, hours_ago=0)
    await session.commit()

    resp = await client.get(
        f"/api/v1/billing/spend/records?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "id" in item
    assert "group_id" in item
    assert "model" in item
    assert "token_count" in item
    assert "cost_usd" in item
    assert "timestamp" in item
    assert item["model"] == "gpt-4o"
    assert item["token_count"] == 750
    assert item["cost_usd"] == 2.50


# ---------------------------------------------------------------------------
# POST /billing/llm-accounts/{id}/revoke — Revoke LLM API Key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_llm_account_key(billing_client):
    """POST /billing/llm-accounts/{id}/revoke clears credentials and marks inactive."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "revoke1@example.com")

    account_id = await _connect_llm_account(client, headers, gid, "openai", "sk-revoke-test")

    # Mock the provider's revoke_key to return True
    mock_provider = MagicMock()
    mock_provider.revoke_key = AsyncMock(return_value=True)

    with patch("src.billing.scheduler.get_provider", return_value=mock_provider):
        resp = await client.post(
            f"/api/v1/billing/llm-accounts/{account_id}/revoke", headers=headers
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["account_id"] == account_id
    assert data["provider_revoked"] is True
    assert data["credentials_cleared"] is True


@pytest.mark.asyncio
async def test_revoke_nonexistent_account(billing_client):
    """POST /billing/llm-accounts/{id}/revoke with bad ID returns 404."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "revoke2@example.com")

    fake_id = uuid4()
    resp = await client.post(
        f"/api/v1/billing/llm-accounts/{fake_id}/revoke", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revoke_already_cleared_account(billing_client):
    """POST /billing/llm-accounts/{id}/revoke on account with no credentials returns false."""
    client, session = billing_client
    headers, gid, user_id = await _setup_auth(client, "revoke3@example.com")

    account_id = await _connect_llm_account(client, headers, gid, "anthropic", "sk-ant-clear")

    # First disconnect to clear credentials
    await client.delete(f"/api/v1/billing/llm-accounts/{account_id}", headers=headers)

    # Now try to revoke — credentials already cleared
    resp = await client.post(
        f"/api/v1/billing/llm-accounts/{account_id}/revoke", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_revoked"] is False
    assert data["credentials_cleared"] is True


@pytest.mark.asyncio
async def test_revoke_requires_auth(billing_client):
    """POST /billing/llm-accounts/{id}/revoke without auth returns 401."""
    client, session = billing_client

    resp = await client.post(f"/api/v1/billing/llm-accounts/{uuid4()}/revoke")
    assert resp.status_code == 401
