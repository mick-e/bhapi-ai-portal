"""Unit tests for billing module — tiers, feature gates, subscriptions, spend, thresholds."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.billing.feature_gate import (
    PLAN_LIMITS,
    get_member_limit,
    get_plan_limits,
    get_platform_limit,
    is_feature_enabled,
)
from src.billing.models import (
    BudgetThreshold,
    FiredThresholdAlert,
    LLMAccount,
    SpendRecord,
    Subscription,
)
from src.billing.plans import PLAN_TIERS, get_all_plans, get_plan
from src.billing.schemas import SubscribeRequest, ThresholdConfig
from src.billing.service import (
    connect_llm_account,
    create_subscription,
    create_threshold,
    disconnect_llm_account,
    get_spend_summary,
    get_subscription,
    list_llm_accounts,
    list_thresholds,
)
from src.billing.tiers import (
    TIERS,
    annual_discount_pct,
    get_all_tiers,
    get_tier,
    get_tier_features,
    get_tier_level,
    tier_has_access,
)
from src.encryption import decrypt_credential
from src.exceptions import ConflictError, NotFoundError
from tests.conftest import make_test_group


# ──────────────────────────────────────────────────────────────────────────────
# 1. Tier configuration
# ──────────────────────────────────────────────────────────────────────────────


class TestTierConfiguration:
    """All 5 tiers have correct features and prices."""

    def test_all_five_tiers_defined(self):
        assert set(TIERS.keys()) == {"free", "family", "family_plus", "school", "enterprise"}

    def test_free_tier_has_no_price(self):
        tier = get_tier("free")
        assert tier["price_monthly"] == 0
        assert tier["price_annual"] == 0
        assert tier["stripe_product_id"] is None

    def test_family_tier_price(self):
        tier = get_tier("family")
        assert tier["price_monthly"] == 9.99
        assert tier["price_annual"] == 95.90

    def test_enterprise_custom_pricing(self):
        tier = get_tier("enterprise")
        assert tier["price_monthly"] is None
        assert tier["price_annual"] is None

    def test_school_unlimited_children(self):
        tier = get_tier("school")
        assert tier["max_children"] is None

    def test_unknown_tier_returns_free(self):
        tier = get_tier("nonexistent")
        assert tier["name"] == "Free"

    def test_tier_hierarchy_levels(self):
        assert get_tier_level("free") == 0
        assert get_tier_level("family") == 1
        assert get_tier_level("enterprise") == 4

    def test_tier_access_comparison(self):
        assert tier_has_access("enterprise", "free") is True
        assert tier_has_access("free", "enterprise") is False
        assert tier_has_access("family", "family") is True

    def test_feature_inheritance(self):
        school_features = get_tier_features("school")
        family_features = get_tier_features("family")
        # School inherits all family features
        for f in family_features:
            assert f in school_features, f"School missing inherited feature: {f}"

    def test_annual_discount_percentage(self):
        pct = annual_discount_pct("family")
        assert pct > 0  # Should have a discount
        assert annual_discount_pct("free") == 0.0

    def test_get_all_tiers_includes_key(self):
        all_tiers = get_all_tiers()
        assert len(all_tiers) == 5
        keys = [t["tier_key"] for t in all_tiers]
        assert "free" in keys
        assert "enterprise" in keys


# ──────────────────────────────────────────────────────────────────────────────
# 2. Feature gate logic
# ──────────────────────────────────────────────────────────────────────────────


class TestFeatureGate:
    """Free tier blocked from premium features; paid tiers get correct access."""

    def test_free_tier_no_pdf_reports(self):
        assert is_feature_enabled("free", "pdf_reports") is False

    def test_free_tier_has_basic_alerts(self):
        assert is_feature_enabled("free", "basic_alerts") is True

    def test_family_tier_has_spend_tracking(self):
        assert is_feature_enabled("family", "spend_tracking") is True

    def test_free_tier_no_blocking_rules(self):
        assert is_feature_enabled("free", "blocking_rules") is False

    def test_enterprise_all_features_enabled(self):
        limits = get_plan_limits("enterprise")
        for feature, enabled in limits["features"].items():
            assert enabled is True, f"Enterprise missing feature: {feature}"

    def test_unknown_plan_falls_back_to_free(self):
        limits = get_plan_limits("nonexistent_plan")
        assert limits == PLAN_LIMITS["free"]

    def test_trialing_gets_family_features(self):
        assert PLAN_LIMITS["trialing"] == PLAN_LIMITS["family"]

    def test_member_limits_per_tier(self):
        assert get_member_limit("free") == 1
        assert get_member_limit("family") == 5
        assert get_member_limit("enterprise") is None

    def test_platform_limits_per_tier(self):
        assert get_platform_limit("free") == 3
        assert get_platform_limit("family") == 10
        assert get_platform_limit("enterprise") is None

    def test_school_has_sis_integration(self):
        assert is_feature_enabled("school", "sis_integration") is True
        assert is_feature_enabled("family", "sis_integration") is False


# ──────────────────────────────────────────────────────────────────────────────
# 3. Subscription state machine
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSubscriptionStateMachine:
    """Subscription lifecycle: create -> active -> cancel -> expired."""

    async def test_create_subscription(self, test_session):
        group, _ = await make_test_group(test_session)
        data = SubscribeRequest(group_id=group.id, plan_type="family", billing_cycle="monthly")
        sub = await create_subscription(test_session, data)
        assert sub.status == "active"
        assert sub.plan_type == "family"

    async def test_duplicate_subscription_rejected(self, test_session):
        group, _ = await make_test_group(test_session)
        data = SubscribeRequest(group_id=group.id, plan_type="family")
        await create_subscription(test_session, data)
        with pytest.raises(ConflictError):
            await create_subscription(test_session, data)

    async def test_subscription_cancelled_allows_new(self, test_session):
        group, _ = await make_test_group(test_session)
        data = SubscribeRequest(group_id=group.id, plan_type="family")
        sub = await create_subscription(test_session, data)
        sub.status = "cancelled"
        await test_session.flush()
        # New subscription should succeed now
        data2 = SubscribeRequest(group_id=group.id, plan_type="school")
        sub2 = await create_subscription(test_session, data2)
        assert sub2.plan_type == "school"

    async def test_get_subscription_not_found(self, test_session):
        with pytest.raises(NotFoundError):
            await get_subscription(test_session, uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# 4. Spend tracking
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSpendTracking:
    """Spend sync accuracy and aggregation."""

    async def test_spend_summary_empty(self, test_session):
        group, _ = await make_test_group(test_session)
        now = datetime.now(timezone.utc)
        summary = await get_spend_summary(
            test_session, group.id,
            period_start=now - timedelta(days=30),
            period_end=now,
        )
        assert summary["total_amount"] == 0.0
        assert summary["record_count"] == 0

    async def test_spend_summary_aggregation(self, test_session):
        from src.billing.schemas import ProviderConnect

        group, _ = await make_test_group(test_session)
        account = await connect_llm_account(
            test_session,
            ProviderConnect(group_id=group.id, provider="openai", api_key="sk-test123"),
        )

        now = datetime.now(timezone.utc)
        for i in range(3):
            record = SpendRecord(
                id=uuid4(),
                group_id=group.id,
                llm_account_id=account.id,
                period_start=now - timedelta(days=1),
                period_end=now,
                amount=10.0 + i,
                currency="USD",
                model="gpt-4",
            )
            test_session.add(record)
        await test_session.flush()

        summary = await get_spend_summary(
            test_session, group.id,
            period_start=now - timedelta(days=2),
            period_end=now + timedelta(hours=1),
        )
        assert summary["total_amount"] == 33.0
        assert summary["record_count"] == 3

    async def test_connect_llm_account_encrypts_key(self, test_session):
        from src.billing.schemas import ProviderConnect

        group, _ = await make_test_group(test_session)
        account = await connect_llm_account(
            test_session,
            ProviderConnect(group_id=group.id, provider="anthropic", api_key="sk-ant-test"),
        )
        assert account.credentials_encrypted is not None
        assert account.credentials_encrypted != "sk-ant-test"
        decrypted = decrypt_credential(account.credentials_encrypted)
        assert decrypted == "sk-ant-test"

    async def test_disconnect_clears_credentials(self, test_session):
        from src.billing.schemas import ProviderConnect

        group, _ = await make_test_group(test_session)
        account = await connect_llm_account(
            test_session,
            ProviderConnect(group_id=group.id, provider="openai", api_key="sk-test"),
        )
        disconnected = await disconnect_llm_account(test_session, account.id)
        assert disconnected.status == "inactive"
        assert disconnected.credentials_encrypted is None

    async def test_duplicate_provider_rejected(self, test_session):
        from src.billing.schemas import ProviderConnect

        group, _ = await make_test_group(test_session)
        data = ProviderConnect(group_id=group.id, provider="openai", api_key="sk-test")
        await connect_llm_account(test_session, data)
        with pytest.raises(ConflictError):
            await connect_llm_account(test_session, data)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Budget thresholds
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBudgetThresholds:
    """Budget threshold creation and firing logic."""

    async def test_create_threshold(self, test_session):
        group, _ = await make_test_group(test_session)
        data = ThresholdConfig(
            group_id=group.id, type="soft", amount=50.0, notify_at=[50, 80, 100],
        )
        threshold = await create_threshold(test_session, data)
        assert threshold.type == "soft"
        assert threshold.amount == 50.0
        assert threshold.notify_at == [50, 80, 100]

    async def test_threshold_fires_at_percentage(self, test_session):
        from src.billing.threshold_checker import check_thresholds

        group, _ = await make_test_group(test_session)
        threshold = BudgetThreshold(
            id=uuid4(), group_id=group.id, type="soft", amount=100.0,
            currency="USD", notify_at=[50, 80, 100],
        )
        test_session.add(threshold)

        # Create an LLM account for the spend record FK
        account = LLMAccount(
            id=uuid4(), group_id=group.id, provider="openai", status="active",
        )
        test_session.add(account)
        await test_session.flush()

        # Add spend that exceeds 50% but not 80%
        now = datetime.now(timezone.utc)
        record = SpendRecord(
            id=uuid4(), group_id=group.id, llm_account_id=account.id,
            period_start=now.replace(day=1), period_end=now,
            amount=55.0, currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        alerts_count = await check_thresholds(test_session, group.id)
        assert alerts_count == 1  # 50% threshold fired

    async def test_threshold_does_not_fire_twice(self, test_session):
        from src.billing.threshold_checker import check_thresholds

        group, _ = await make_test_group(test_session)
        threshold = BudgetThreshold(
            id=uuid4(), group_id=group.id, type="hard", amount=100.0,
            currency="USD", notify_at=[50],
        )
        test_session.add(threshold)
        account = LLMAccount(
            id=uuid4(), group_id=group.id, provider="openai", status="active",
        )
        test_session.add(account)
        await test_session.flush()

        now = datetime.now(timezone.utc)
        record = SpendRecord(
            id=uuid4(), group_id=group.id, llm_account_id=account.id,
            period_start=now.replace(day=1), period_end=now,
            amount=60.0, currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        first_run = await check_thresholds(test_session, group.id)
        assert first_run == 1
        second_run = await check_thresholds(test_session, group.id)
        assert second_run == 0  # Should not fire again

    async def test_list_thresholds(self, test_session):
        group, _ = await make_test_group(test_session)
        data1 = ThresholdConfig(group_id=group.id, type="soft", amount=50.0)
        data2 = ThresholdConfig(group_id=group.id, type="hard", amount=100.0)
        await create_threshold(test_session, data1)
        await create_threshold(test_session, data2)
        thresholds = await list_thresholds(test_session, group.id)
        assert len(thresholds) == 2


# ──────────────────────────────────────────────────────────────────────────────
# 6. Plan definitions
# ──────────────────────────────────────────────────────────────────────────────


class TestPlanDefinitions:
    """PLAN_TIERS definitions in plans.py."""

    def test_all_plans_defined(self):
        assert set(PLAN_TIERS.keys()) == {
            "free",
            "family",
            "bundle",
            "school",
            "school_pilot",
            "enterprise",
        }

    def test_get_plan_returns_none_for_unknown(self):
        assert get_plan("nonexistent") is None

    def test_get_all_plans_structure(self):
        plans = get_all_plans()
        assert all("plan_type" in p for p in plans)
        assert len(plans) == 6

    def test_school_has_per_seat_pricing(self):
        school = get_plan("school")
        assert school is not None
        assert "price_unit" in school
        assert school["price_unit"] == "per student/month"

    def test_school_priced_at_1_99_per_seat(self):
        """R-22: School tier reduced from $2.99 to $1.99 to undercut GoGuardian/Gaggle."""
        school = get_plan("school")
        assert school["price_monthly"] == 1.99
        assert school["price_annual"] == 19.99
        assert school["plan_version"] == "school_v2"

    def test_school_pilot_is_free_and_capped(self):
        """R-22: School Pilot is free for 90 days, capped at 50 seats, auto-converts."""
        pilot = get_plan("school_pilot")
        assert pilot is not None
        assert pilot["price_monthly"] == 0
        assert pilot["price_annual"] == 0
        assert pilot["member_limit"] == 50
        assert pilot["duration_days"] == 90
        assert pilot["auto_convert_to"] == "school"
