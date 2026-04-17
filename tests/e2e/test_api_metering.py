"""End-to-end tests for API platform rate tiers and usage metering."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import ApiKey, User
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def meter_engine():
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
async def meter_session(meter_engine):
    session = AsyncSession(meter_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def meter_data(meter_session):
    """Seed a user, group, and API key for metering tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"meter-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Meter Test User",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    admin_user = User(
        id=uuid.uuid4(),
        email=f"meter-admin-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Meter Admin",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    meter_session.add_all([user, admin_user])
    await meter_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Meter Test Group",
        type="family",
        owner_id=user.id,
        settings={},
    )
    meter_session.add(group)
    await meter_session.flush()

    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=user.id,
        group_id=group.id,
        name="Test Metering Key",
        key_hash="sha256_fake_hash_for_testing_" + uuid.uuid4().hex,
        key_prefix="bhapi_sk_test",
    )
    meter_session.add(api_key)
    await meter_session.flush()
    await meter_session.commit()

    return {
        "user": user,
        "admin_user": admin_user,
        "group": group,
        "api_key": api_key,
    }


@pytest_asyncio.fixture
async def meter_client(meter_engine, meter_session, meter_data):
    """HTTP client authenticated as the metering test user."""
    app = create_app()

    async def get_db_override():
        try:
            yield meter_session
            await meter_session.commit()
        except Exception:
            await meter_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=meter_data["user"].id,
            group_id=meter_data["group"].id,
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
        yield ac, meter_data


@pytest_asyncio.fixture
async def meter_admin_client(meter_engine, meter_session, meter_data):
    """HTTP client authenticated as an admin for metering tests."""
    app = create_app()

    async def get_db_override():
        try:
            yield meter_session
            await meter_session.commit()
        except Exception:
            await meter_session.rollback()
            raise

    async def fake_admin_auth():
        return GroupContext(
            user_id=meter_data["admin_user"].id,
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
        yield ac, meter_data


# ---------------------------------------------------------------------------
# Rate tier listing (public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_rate_tiers(meter_client):
    """GET /api/v1/platform/rate-tiers returns all 4 public tiers."""
    ac, _ = meter_client
    resp = await ac.get("/api/v1/platform/rate-tiers")
    assert resp.status_code == 200
    tiers = resp.json()
    assert isinstance(tiers, list)
    assert len(tiers) == 4
    names = {t["name"] for t in tiers}
    assert names == {"free", "developer", "business", "enterprise"}


@pytest.mark.asyncio
async def test_rate_tier_structure(meter_client):
    """Each rate tier has the expected fields."""
    ac, _ = meter_client
    resp = await ac.get("/api/v1/platform/rate-tiers")
    assert resp.status_code == 200
    for tier in resp.json():
        assert "name" in tier
        assert "monthly_request_quota" in tier
        assert "requests_per_minute" in tier
        assert "webhooks_enabled" in tier
        assert "sandbox_only" in tier
        assert "price_monthly" in tier


@pytest.mark.asyncio
async def test_free_tier_is_sandbox_only(meter_client):
    """Free tier should be sandbox-only with webhooks disabled."""
    ac, _ = meter_client
    resp = await ac.get("/api/v1/platform/rate-tiers")
    free = next(t for t in resp.json() if t["name"] == "free")
    assert free["sandbox_only"] is True
    assert free["webhooks_enabled"] is False
    assert free["price_monthly"] == 0.0
    assert free["monthly_request_quota"] == 10_000


@pytest.mark.asyncio
async def test_enterprise_tier_values(meter_client):
    """Enterprise tier should have highest limits."""
    ac, _ = meter_client
    resp = await ac.get("/api/v1/platform/rate-tiers")
    ent = next(t for t in resp.json() if t["name"] == "enterprise")
    assert ent["monthly_request_quota"] == 10_000_000
    assert ent["requests_per_minute"] == 6000
    assert ent["webhooks_enabled"] is True
    assert ent["sandbox_only"] is False


# ---------------------------------------------------------------------------
# Tier assignment (admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_tier_admin(meter_admin_client):
    """Admin can assign a developer tier to an API key."""
    ac, data = meter_admin_client
    resp = await ac.post("/api/v1/platform/metering/assign-tier", json={
        "api_key_id": str(data["api_key"].id),
        "tier_name": "developer",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "developer"
    assert body["quota_limit"] == 100_000
    assert body["requests_per_minute"] == 300


@pytest.mark.asyncio
async def test_assign_tier_non_admin_forbidden(meter_client):
    """Non-admin users cannot assign tiers."""
    ac, data = meter_client
    resp = await ac.post("/api/v1/platform/metering/assign-tier", json={
        "api_key_id": str(data["api_key"].id),
        "tier_name": "business",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_assign_invalid_tier(meter_admin_client):
    """Assigning an invalid tier name returns 422."""
    ac, data = meter_admin_client
    resp = await ac.post("/api/v1/platform/metering/assign-tier", json={
        "api_key_id": str(data["api_key"].id),
        "tier_name": "godmode",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assign_tier_updates_existing(meter_admin_client):
    """Assigning a new tier updates the existing mapping."""
    ac, data = meter_admin_client
    key_id = str(data["api_key"].id)

    # Assign developer first
    resp1 = await ac.post("/api/v1/platform/metering/assign-tier", json={
        "api_key_id": key_id,
        "tier_name": "developer",
    })
    assert resp1.status_code == 200
    assert resp1.json()["tier"] == "developer"

    # Upgrade to business
    resp2 = await ac.post("/api/v1/platform/metering/assign-tier", json={
        "api_key_id": key_id,
        "tier_name": "business",
    })
    assert resp2.status_code == 200
    assert resp2.json()["tier"] == "business"
    assert resp2.json()["quota_limit"] == 1_000_000


# ---------------------------------------------------------------------------
# Usage recording and retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_default_free_tier(meter_client):
    """Usage stats for a fresh key default to free tier."""
    ac, data = meter_client
    resp = await ac.get(
        "/api/v1/platform/metering/usage",
        params={"api_key_id": str(data["api_key"].id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["request_count"] == 0
    assert body["quota_limit"] == 10_000
    assert body["quota_remaining"] == 10_000


@pytest.mark.asyncio
async def test_record_and_retrieve_usage(meter_admin_client, meter_session):
    """Recording usage increments the monthly aggregate."""
    from src.api_platform.metering_service import record_usage

    ac, data = meter_admin_client
    key_id = data["api_key"].id

    # Record some requests
    await record_usage(meter_session, key_id, "/api/v1/alerts", 200, 45)
    await record_usage(meter_session, key_id, "/api/v1/alerts", 200, 55)
    await record_usage(meter_session, key_id, "/api/v1/groups", 500, 120)
    await meter_session.flush()

    resp = await ac.get(
        "/api/v1/platform/metering/usage",
        params={"api_key_id": str(key_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_count"] == 3
    assert body["error_count"] == 1  # the 500 response
    assert body["quota_remaining"] == 10_000 - 3  # free tier default


@pytest.mark.asyncio
async def test_quota_check_within_limit(meter_session, meter_data):
    """Fresh key should be within quota."""
    from src.api_platform.metering_service import check_quota

    result = await check_quota(meter_session, meter_data["api_key"].id)
    assert result is True


@pytest.mark.asyncio
async def test_usage_after_tier_upgrade(meter_admin_client, meter_session):
    """After upgrading tier, quota_limit reflects new tier."""
    from src.api_platform.metering_service import assign_tier, record_usage

    ac, data = meter_admin_client
    key_id = data["api_key"].id

    # Record usage
    await record_usage(meter_session, key_id, "/api/v1/test", 200, 10)
    await meter_session.flush()

    # Assign business tier
    await assign_tier(meter_session, key_id, "business")
    await meter_session.flush()

    resp = await ac.get(
        "/api/v1/platform/metering/usage",
        params={"api_key_id": str(key_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "business"
    assert body["quota_limit"] == 1_000_000
    assert body["request_count"] == 1
    assert body["quota_remaining"] == 999_999
