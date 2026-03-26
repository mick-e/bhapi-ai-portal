"""E2E tests for bundle pricing — GET /tiers, GET /my-tier, POST /upgrade."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.models import FeatureGate, Subscription
from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Shared single-session fixture (matches billing_endpoints pattern)
# ---------------------------------------------------------------------------

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def bp_client():
    """Single-session test client for bundle pricing tests."""
    engine = create_async_engine(
        TEST_DB,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def _override_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, session

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client, email: str) -> str:
    res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1!",
        "display_name": "Bundle Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


async def _setup(client, email: str):
    """Register and return (headers, group_id) where group_id is the auto-created group."""
    token = await _register(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    # Get the group_id from auth/me (auto-created on registration)
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200, me_res.text
    gid = me_res.json().get("group_id")
    return headers, gid


# ---------------------------------------------------------------------------
# GET /api/v1/billing/tiers — public endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tiers_endpoint_is_public(bp_client):
    """GET /tiers returns 200 without auth."""
    client, _ = bp_client
    res = await client.get("/api/v1/billing/tiers")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_tiers_returns_all_five(bp_client):
    """Tiers endpoint lists all 5 tiers."""
    client, _ = bp_client
    res = await client.get("/api/v1/billing/tiers")
    data = res.json()
    assert "tiers" in data
    assert len(data["tiers"]) == 5


@pytest.mark.asyncio
async def test_tiers_includes_free(bp_client):
    client, _ = bp_client
    keys = [t["tier_key"] for t in (await client.get("/api/v1/billing/tiers")).json()["tiers"]]
    assert "free" in keys


@pytest.mark.asyncio
async def test_tiers_includes_family_plus(bp_client):
    client, _ = bp_client
    keys = [t["tier_key"] for t in (await client.get("/api/v1/billing/tiers")).json()["tiers"]]
    assert "family_plus" in keys


@pytest.mark.asyncio
async def test_tier_response_has_required_fields(bp_client):
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    family = next(t for t in tiers if t["tier_key"] == "family")
    assert family["name"] == "Family"
    assert family["price_monthly"] == 9.99
    assert family["price_annual"] == 95.90
    assert isinstance(family["features"], list)
    assert len(family["features"]) > 0


@pytest.mark.asyncio
async def test_free_tier_has_zero_price(bp_client):
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    free = next(t for t in tiers if t["tier_key"] == "free")
    assert free["price_monthly"] == 0
    assert free["price_annual"] == 0


@pytest.mark.asyncio
async def test_enterprise_tier_has_null_price(bp_client):
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    ent = next(t for t in tiers if t["tier_key"] == "enterprise")
    assert ent["price_monthly"] is None


@pytest.mark.asyncio
async def test_family_plus_inherits_family_features(bp_client):
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    family = next(t for t in tiers if t["tier_key"] == "family")
    family_plus = next(t for t in tiers if t["tier_key"] == "family_plus")
    for f in family["features"]:
        assert f in family_plus["features"], f"Missing inherited feature: {f}"


# ---------------------------------------------------------------------------
# GET /api/v1/billing/my-tier — authenticated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_tier_requires_auth(bp_client):
    """GET /my-tier returns 401 without token."""
    client, _ = bp_client
    res = await client.get("/api/v1/billing/my-tier")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_my_tier_free_user(bp_client):
    """New user with no explicit subscription is on free tier."""
    client, session = bp_client
    headers, gid = await _setup(client, "my-tier-free@example.com")
    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["current_tier"] == "free"
    assert data["tier_name"] == "Free"
    assert isinstance(data["features"], list)
    assert isinstance(data["upgrade_options"], list)
    assert len(data["upgrade_options"]) > 0


@pytest.mark.asyncio
async def test_my_tier_family_subscription(bp_client):
    """User with active family subscription sees family tier."""
    import uuid as _uuid
    client, session = bp_client
    headers, gid = await _setup(client, "my-tier-family@example.com")

    sub = Subscription(
        id=uuid4(),
        group_id=_uuid.UUID(gid),
        plan_type="family",
        billing_cycle="monthly",
        status="active",
    )
    session.add(sub)
    await session.flush()

    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["current_tier"] == "family"
    assert "real_time_alerts" in data["features"]


@pytest.mark.asyncio
async def test_my_tier_upgrade_options_excludes_current(bp_client):
    """Upgrade options do not include the current tier or lower tiers."""
    import uuid as _uuid
    client, session = bp_client
    headers, gid = await _setup(client, "upgrade-options@example.com")

    sub = Subscription(
        id=uuid4(),
        group_id=_uuid.UUID(gid),
        plan_type="family",
        billing_cycle="monthly",
        status="active",
    )
    session.add(sub)
    await session.flush()

    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    data = res.json()
    upgrade_keys = [t["tier_key"] for t in data["upgrade_options"]]
    assert "family" not in upgrade_keys
    assert "free" not in upgrade_keys


@pytest.mark.asyncio
async def test_my_tier_enterprise_has_no_upgrades(bp_client):
    """Enterprise user has no upgrade options."""
    import uuid as _uuid
    client, session = bp_client
    headers, gid = await _setup(client, "enterprise-no-upgrade@example.com")

    sub = Subscription(
        id=uuid4(),
        group_id=_uuid.UUID(gid),
        plan_type="enterprise",
        billing_cycle="annual",
        status="active",
    )
    session.add(sub)
    await session.flush()

    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    data = res.json()
    assert data["upgrade_options"] == []


# ---------------------------------------------------------------------------
# Feature gate full flow via check_tier_access service function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_free_user_blocked_from_family_plus_feature(bp_client):
    """Direct service check: free user blocked from family_plus gate."""
    _, session = bp_client
    from src.billing.feature_gate import check_tier_access
    from src.exceptions import ForbiddenError
    from tests.conftest import make_test_group

    group, _ = await make_test_group(session)
    gate = FeatureGate(id=uuid4(), feature_key="e2e_location", required_tier="family_plus")
    session.add(gate)
    await session.flush()

    with pytest.raises(ForbiddenError):
        await check_tier_access(session, group.id, "e2e_location")


@pytest.mark.asyncio
async def test_upgrade_enables_gated_feature(bp_client):
    """After upgrading to family_plus, gate access is granted."""
    _, session = bp_client
    from src.billing.feature_gate import check_tier_access
    from tests.conftest import make_test_group

    group, _ = await make_test_group(session)
    gate = FeatureGate(id=uuid4(), feature_key="e2e_location2", required_tier="family_plus")
    sub = Subscription(
        id=uuid4(),
        group_id=group.id,
        plan_type="family_plus",
        billing_cycle="monthly",
        status="active",
    )
    session.add(gate)
    session.add(sub)
    await session.flush()

    # Should not raise
    await check_tier_access(session, group.id, "e2e_location2")


@pytest.mark.asyncio
async def test_school_user_can_access_family_feature(bp_client):
    """School tier (higher) can access family-gated features."""
    _, session = bp_client
    from src.billing.feature_gate import check_tier_access
    from tests.conftest import make_test_group

    group, _ = await make_test_group(session)
    gate = FeatureGate(id=uuid4(), feature_key="e2e_reports", required_tier="family")
    sub = Subscription(
        id=uuid4(),
        group_id=group.id,
        plan_type="school",
        billing_cycle="monthly",
        status="active",
    )
    session.add(gate)
    session.add(sub)
    await session.flush()

    await check_tier_access(session, group.id, "e2e_reports")


# ---------------------------------------------------------------------------
# POST /api/v1/billing/upgrade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upgrade_requires_auth(bp_client):
    """POST /upgrade without token returns 401."""
    client, _ = bp_client
    res = await client.post("/api/v1/billing/upgrade", json={"plan_type": "family"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_upgrade_returns_checkout_url(bp_client):
    """POST /upgrade returns a Stripe checkout URL."""
    client, _ = bp_client
    headers, gid = await _setup(client, "upgrade-endpoint@example.com")

    mock_session = MagicMock()
    mock_session.id = "cs_test_abc123"
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc123"

    with patch("src.billing.stripe_client._get_stripe") as mock_stripe:
        stripe_mod = MagicMock()
        stripe_mod.Customer.list.return_value = MagicMock(data=[MagicMock(id="cus_test123")])
        stripe_mod.checkout.Session.create.return_value = mock_session
        stripe_mod.StripeError = Exception
        mock_stripe.return_value = stripe_mod

        res = await client.post(
            "/api/v1/billing/upgrade",
            json={"plan_type": "family", "billing_cycle": "monthly"},
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert "checkout_url" in data
    assert "stripe.com" in data["checkout_url"]


@pytest.mark.asyncio
async def test_upgrade_invalid_plan_type_returns_422(bp_client):
    """POST /upgrade with unknown plan_type returns 422 validation error."""
    client, _ = bp_client
    headers, _ = await _setup(client, "upgrade-invalid@example.com")
    res = await client.post(
        "/api/v1/billing/upgrade",
        json={"plan_type": "turbo_ultra"},
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_upgrade_family_plus_plan(bp_client):
    """POST /upgrade accepts family_plus as a valid plan_type (schema-level validation)."""
    client, _ = bp_client
    headers, _ = await _setup(client, "upgrade-family-plus@example.com")

    # Patch create_checkout_session_for_group to bypass PLAN_PRICES lookup
    with patch("src.billing.router.create_checkout_session_for_group") as mock_checkout:
        mock_checkout.return_value = {
            "session_id": "cs_test_fp",
            "url": "https://checkout.stripe.com/pay/cs_test_fp",
        }
        res = await client.post(
            "/api/v1/billing/upgrade",
            json={"plan_type": "family_plus", "billing_cycle": "monthly"},
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert "checkout_url" in data
    # Verify the service was called with family_plus
    mock_checkout.assert_called_once()
    call_kwargs = mock_checkout.call_args.kwargs
    assert call_kwargs.get("plan_type") == "family_plus"


@pytest.mark.asyncio
async def test_upgrade_annual_billing_cycle(bp_client):
    """POST /upgrade with annual billing_cycle is accepted."""
    client, _ = bp_client
    headers, _ = await _setup(client, "upgrade-annual@example.com")

    mock_session = MagicMock()
    mock_session.id = "cs_test_annual"
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_annual"

    with patch("src.billing.stripe_client._get_stripe") as mock_stripe:
        stripe_mod = MagicMock()
        stripe_mod.Customer.list.return_value = MagicMock(data=[MagicMock(id="cus_annual")])
        stripe_mod.checkout.Session.create.return_value = mock_session
        stripe_mod.StripeError = Exception
        mock_stripe.return_value = stripe_mod

        res = await client.post(
            "/api/v1/billing/upgrade",
            json={"plan_type": "school", "billing_cycle": "annual"},
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data.get("session_id") == "cs_test_annual"


@pytest.mark.asyncio
async def test_upgrade_response_has_session_id(bp_client):
    """POST /upgrade response includes session_id field."""
    client, _ = bp_client
    headers, _ = await _setup(client, "upgrade-session-id@example.com")

    with patch("src.billing.router.create_checkout_session_for_group") as mock_checkout:
        mock_checkout.return_value = {
            "session_id": "cs_test_sid",
            "url": "https://checkout.stripe.com/pay/cs_test_sid",
        }
        res = await client.post(
            "/api/v1/billing/upgrade",
            json={"plan_type": "school", "billing_cycle": "annual"},
            headers=headers,
        )
    assert res.status_code == 200
    assert res.json()["session_id"] == "cs_test_sid"


# ---------------------------------------------------------------------------
# GET /api/v1/billing/tiers — additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tiers_school_features_include_sis(bp_client):
    """School tier advertises SIS integration feature."""
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    school = next(t for t in tiers if t["tier_key"] == "school")
    " ".join(school["features"]).lower()
    assert any("sis" in f or "integration" in f for f in school["features"]), (
        f"SIS/integration feature not found in school tier features: {school['features']}"
    )


@pytest.mark.asyncio
async def test_tiers_tier_order_matches_hierarchy(bp_client):
    """Tiers list keys match expected hierarchy order (free → enterprise)."""
    client, _ = bp_client
    tiers = (await client.get("/api/v1/billing/tiers")).json()["tiers"]
    keys = [t["tier_key"] for t in tiers]
    expected_order = ["free", "family", "family_plus", "school", "enterprise"]
    assert keys == expected_order, f"Tier order mismatch: {keys}"


# ---------------------------------------------------------------------------
# GET /api/v1/billing/my-tier — additional coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_tier_returns_price_fields(bp_client):
    """GET /my-tier includes price_monthly and price_annual fields."""
    client, _ = bp_client
    headers, _ = await _setup(client, "my-tier-prices@example.com")
    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "price_monthly" in data
    assert "price_annual" in data


@pytest.mark.asyncio
async def test_my_tier_trialing_user_gets_family_features(bp_client):
    """User with trialing status is treated as family tier."""
    import uuid as _uuid
    client, session = bp_client
    headers, gid = await _setup(client, "my-tier-trial@example.com")

    sub = Subscription(
        id=uuid4(),
        group_id=_uuid.UUID(gid),
        plan_type="family",
        billing_cycle="monthly",
        status="trialing",
    )
    session.add(sub)
    await session.flush()

    res = await client.get("/api/v1/billing/my-tier", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["current_tier"] == "family"
    assert len(data["features"]) > 0
