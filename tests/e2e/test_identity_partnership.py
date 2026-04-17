"""E2E tests for the Family+ identity-protection partner integration.

Covers:
- POST /api/v1/billing/identity-protection/activate (happy path + 403/422 paths)
- GET  /api/v1/billing/identity-protection/status
- POST /api/v1/billing/identity-protection/cancel

Uses the in-memory MockPartnerClient (no external API calls).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.models import Subscription
from src.billing.partnerships import reset_partner_client
from src.database import Base, get_db
from src.main import create_app


@pytest.fixture(autouse=True)
def _reset_mock_partner():
    """Each test gets a fresh partner client singleton."""
    reset_partner_client()
    yield
    reset_partner_client()


@pytest.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def override_get_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, session

    await session.close()
    await engine.dispose()


async def _register(ac, email):
    """Register a family user. Returns (token, user_id, group_id) — group is
    auto-created at registration and bound to the auth context."""
    resp = await ac.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass1",
            "display_name": "Identity Tester",
            "account_type": "family",
            "privacy_notice_accepted": True,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    return body["access_token"], body["user"]["id"], body["user"]["group_id"]


async def _seed_subscription(session, group_id: UUID, plan_type: str):
    sub = Subscription(
        id=uuid4(),
        group_id=group_id,
        plan_type=plan_type,
        billing_cycle="monthly",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    session.add(sub)
    await session.commit()
    return sub


@pytest.mark.asyncio
async def test_family_plus_user_can_activate_identity_protection(client):
    """Family+ subscriber with explicit consent gets a partner account provisioned."""
    ac, session = client
    token, user_id, gid = await _register(ac, "fam-plus-1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    resp = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["partner_name"] == "mock"
    assert body["partner_account_id"].startswith("mock-")
    assert body["consent_text_version"] == "v1"


@pytest.mark.asyncio
async def test_activation_requires_explicit_consent(client):
    """Activation rejects requests without ``agreed: True``."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    resp = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": False},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_activation_rejects_stale_consent_version(client):
    """If the user's consent text version doesn't match, reject."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    resp = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v0", "agreed": True},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_base_family_user_blocked_from_activation(client):
    """A regular Family subscriber (not Family+) is denied — 403 gated."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-base-1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family")  # not family_plus

    resp = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_status_endpoint_reflects_enrollment(client):
    """Status endpoint returns ``enrolled: false`` initially, then true after activation."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    pre = await ac.get("/api/v1/billing/identity-protection/status", headers=headers)
    assert pre.status_code == 200
    assert pre.json()["enrolled"] is False
    assert pre.json()["current_consent_text_version"] == "v1"

    await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )

    post = await ac.get("/api/v1/billing/identity-protection/status", headers=headers)
    assert post.status_code == 200
    body = post.json()
    assert body["enrolled"] is True
    assert body["status"] == "active"
    assert body["partner_name"] == "mock"


@pytest.mark.asyncio
async def test_cancel_revokes_active_link(client):
    """Cancel endpoint flips status to cancelled and returns revoked=true."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )
    cancel = await ac.post(
        "/api/v1/billing/identity-protection/cancel", headers=headers
    )
    assert cancel.status_code == 200
    assert cancel.json()["revoked"] is True

    status = await ac.get(
        "/api/v1/billing/identity-protection/status", headers=headers
    )
    assert status.json()["enrolled"] is False
    assert status.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_when_not_enrolled_returns_false(client):
    """Cancelling when no link exists returns revoked=false (not an error)."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    resp = await ac.post(
        "/api/v1/billing/identity-protection/cancel", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] is False


@pytest.mark.asyncio
async def test_double_activation_conflicts(client):
    """Activating twice without cancelling returns 409 Conflict."""
    ac, session = client
    token, _, gid = await _register(ac, "fam-plus-7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await _seed_subscription(session, UUID(gid), "family_plus")

    first = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )
    assert first.status_code == 201

    second = await ac.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=headers,
    )
    assert second.status_code == 409, second.text
