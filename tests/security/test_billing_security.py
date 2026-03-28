"""Security tests for billing module — webhook validation, data isolation, tier enforcement."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.feature_gate import (
    get_group_plan,
    is_feature_enabled,
    require_feature,
)
from src.billing.models import LLMAccount, SpendRecord, Subscription
from src.billing.schemas import ProviderConnect, SubscribeRequest, ThresholdConfig
from src.billing.service import (
    connect_llm_account,
    create_subscription,
    create_threshold,
    get_spend_summary,
    list_llm_accounts,
)
from src.billing.stripe_client import StripeError, verify_webhook_signature
from src.billing.tiers import get_tier_features, tier_has_access
from src.database import Base, get_db
from src.exceptions import ForbiddenError
from src.main import create_app
from tests.conftest import make_test_group


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: security test client with committing sessions
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def billing_sec_client():
    """Security test client for billing endpoints."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine.sync_engine, "connect")
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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


async def _register_and_login(client, email, password="SecurePass1!", display_name="User"):
    """Register a user and return auth headers."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "display_name": display_name,
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────────────────────────────────────
# 1. Webhook signature validation
# ──────────────────────────────────────────────────────────────────────────────


class TestWebhookSignatureValidation:
    """Stripe webhook rejects invalid signatures."""

    def test_missing_webhook_secret_raises(self, monkeypatch):
        """verify_webhook_signature raises if STRIPE_WEBHOOK_SECRET is not set."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
        # Clear settings cache
        from src.config import get_settings
        get_settings.cache_clear()
        try:
            with pytest.raises(StripeError, match="not configured"):
                verify_webhook_signature(b'{"type": "test"}', "sig_invalid")
        finally:
            get_settings.cache_clear()

    def test_invalid_signature_rejected(self, monkeypatch):
        """Invalid signature should raise StripeError."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
        from src.config import get_settings
        get_settings.cache_clear()
        try:
            with pytest.raises(StripeError):
                verify_webhook_signature(b'{"type": "test"}', "sig_totally_invalid")
        finally:
            get_settings.cache_clear()


# ──────────────────────────────────────────────────────────────────────────────
# 2. Webhook endpoint rejects bad requests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_endpoint_no_signature(billing_sec_client):
    """POST to /webhooks without Stripe-Signature header should fail."""
    resp = await billing_sec_client.post(
        "/api/v1/billing/webhooks",
        content=b'{"type": "test"}',
        headers={"Content-Type": "application/json"},
    )
    # Should fail with 422 (validation error from StripeError) or 401
    assert resp.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_webhook_endpoint_empty_signature(billing_sec_client):
    """POST with empty Stripe-Signature should fail."""
    resp = await billing_sec_client.post(
        "/api/v1/billing/webhooks",
        content=b'{"type": "test"}',
        headers={"Content-Type": "application/json", "Stripe-Signature": ""},
    )
    assert resp.status_code in (401, 422, 500)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Cross-group spend data isolation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSpendDataIsolation:
    """Groups cannot see each other's spend data (regression for A3-4)."""

    async def test_spend_isolated_between_groups(self, test_session):
        group_a, _ = await make_test_group(test_session, name="Group A")
        group_b, _ = await make_test_group(test_session, name="Group B")

        # Create LLM accounts for both groups
        account_a = LLMAccount(
            id=uuid4(), group_id=group_a.id, provider="openai", status="active",
        )
        account_b = LLMAccount(
            id=uuid4(), group_id=group_b.id, provider="openai", status="active",
        )
        test_session.add_all([account_a, account_b])
        await test_session.flush()

        now = datetime.now(timezone.utc)
        # Add spend to group A
        record_a = SpendRecord(
            id=uuid4(), group_id=group_a.id, llm_account_id=account_a.id,
            period_start=now - timedelta(days=1), period_end=now,
            amount=100.0, currency="USD",
        )
        # Add spend to group B
        record_b = SpendRecord(
            id=uuid4(), group_id=group_b.id, llm_account_id=account_b.id,
            period_start=now - timedelta(days=1), period_end=now,
            amount=200.0, currency="USD",
        )
        test_session.add_all([record_a, record_b])
        await test_session.flush()

        # Group A should only see its own spend
        summary_a = await get_spend_summary(
            test_session, group_a.id,
            period_start=now - timedelta(days=2), period_end=now + timedelta(hours=1),
        )
        assert summary_a["total_amount"] == 100.0

        # Group B should only see its own spend
        summary_b = await get_spend_summary(
            test_session, group_b.id,
            period_start=now - timedelta(days=2), period_end=now + timedelta(hours=1),
        )
        assert summary_b["total_amount"] == 200.0

    async def test_llm_accounts_isolated_between_groups(self, test_session):
        group_a, _ = await make_test_group(test_session, name="Group A")
        group_b, _ = await make_test_group(test_session, name="Group B")

        data_a = ProviderConnect(group_id=group_a.id, provider="openai", api_key="sk-a")
        data_b = ProviderConnect(group_id=group_b.id, provider="openai", api_key="sk-b")
        await connect_llm_account(test_session, data_a)
        await connect_llm_account(test_session, data_b)

        accounts_a = await list_llm_accounts(test_session, group_a.id)
        accounts_b = await list_llm_accounts(test_session, group_b.id)
        assert len(accounts_a) == 1
        assert len(accounts_b) == 1
        assert accounts_a[0].group_id == group_a.id
        assert accounts_b[0].group_id == group_b.id


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tier enforcement cannot be bypassed
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTierEnforcement:
    """Feature gate enforcement per tier."""

    async def test_free_group_cannot_access_premium_feature(self, test_session):
        group, _ = await make_test_group(test_session)
        # No subscription = free tier
        with pytest.raises(ForbiddenError, match="upgrade"):
            await require_feature(test_session, group.id, "pdf_reports")

    async def test_family_group_can_access_family_feature(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="active",
        )
        test_session.add(sub)
        await test_session.flush()

        # Should not raise
        await require_feature(test_session, group.id, "pdf_reports")

    async def test_family_group_blocked_from_school_feature(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="active",
        )
        test_session.add(sub)
        await test_session.flush()

        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "sis_integration")

    async def test_cancelled_subscription_reverts_to_free(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="cancelled",
        )
        test_session.add(sub)
        await test_session.flush()

        plan = await get_group_plan(test_session, group.id)
        assert plan == "free"

    async def test_trialing_subscription_gets_family_features(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="trialing",
        )
        test_session.add(sub)
        await test_session.flush()

        plan = await get_group_plan(test_session, group.id)
        assert plan == "trialing"
        assert is_feature_enabled("trialing", "pdf_reports") is True

    async def test_past_due_subscription_retains_access(self, test_session):
        """past_due should still have plan access (grace period)."""
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="school",
            billing_cycle="monthly", status="past_due",
        )
        test_session.add(sub)
        await test_session.flush()

        plan = await get_group_plan(test_session, group.id)
        assert plan == "school"


# ──────────────────────────────────────────────────────────────────────────────
# 5. Feature gates enforce correctly per tier
# ──────────────────────────────────────────────────────────────────────────────


class TestFeatureGateEnforcement:
    """Static feature gate enforcement checks."""

    def test_free_tier_has_no_sso(self):
        assert is_feature_enabled("free", "sso") is False

    def test_school_tier_has_sso(self):
        assert is_feature_enabled("school", "sso") is True

    def test_family_tier_no_webhooks(self):
        assert is_feature_enabled("family", "webhooks") is False

    def test_enterprise_has_custom_taxonomy(self):
        assert is_feature_enabled("enterprise", "custom_taxonomy") is True

    def test_nonexistent_feature_returns_false(self):
        assert is_feature_enabled("enterprise", "nonexistent_feature") is False


# ──────────────────────────────────────────────────────────────────────────────
# 6. Tier hierarchy cannot be bypassed
# ──────────────────────────────────────────────────────────────────────────────


class TestTierHierarchy:
    """Tier access checks cannot be bypassed."""

    def test_free_cannot_bypass_to_enterprise(self):
        assert tier_has_access("free", "enterprise") is False

    def test_family_cannot_access_school(self):
        assert tier_has_access("family", "school") is False

    def test_unknown_tier_treated_as_free(self):
        from src.billing.tiers import get_tier_level
        assert get_tier_level("hacker_tier") == 0

    def test_enterprise_features_include_all_lower_tiers(self):
        enterprise = get_tier_features("enterprise")
        school = get_tier_features("school")
        for f in school:
            assert f in enterprise, f"Enterprise missing school feature: {f}"


# ──────────────────────────────────────────────────────────────────────────────
# 7. API key scoping on billing endpoints
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_billing_endpoints_require_auth(billing_sec_client):
    """Billing endpoints that need auth should reject unauthenticated requests."""
    # subscription status
    resp = await billing_sec_client.get("/api/v1/billing/subscription")
    assert resp.status_code in (401, 403)

    # features
    resp = await billing_sec_client.get("/api/v1/billing/features")
    assert resp.status_code in (401, 403)

    # spend
    resp = await billing_sec_client.get("/api/v1/billing/spend")
    assert resp.status_code in (401, 403)

    # thresholds
    resp = await billing_sec_client.get("/api/v1/billing/thresholds")
    assert resp.status_code in (401, 403)

    # my-tier
    resp = await billing_sec_client.get("/api/v1/billing/my-tier")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_public_endpoints_accessible_without_auth(billing_sec_client):
    """Public billing endpoints should be accessible without auth."""
    # plans (public)
    resp = await billing_sec_client.get("/api/v1/billing/plans")
    assert resp.status_code == 200

    # tiers (public)
    resp = await billing_sec_client.get("/api/v1/billing/tiers")
    assert resp.status_code == 200

    # platform safety (public)
    resp = await billing_sec_client.get("/api/v1/billing/platform-safety")
    assert resp.status_code == 200

    # vendor risk (public)
    resp = await billing_sec_client.get("/api/v1/billing/vendor-risk")
    assert resp.status_code == 200
