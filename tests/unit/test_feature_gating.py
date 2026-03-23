"""Unit tests for Phase 3 feature gating — tiers.py + feature_gate.py DB-backed checks."""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.billing.feature_gate import (
    TIER_HIERARCHY,
    check_tier_access,
)
from src.billing.models import FeatureGate, Subscription
from src.billing.tiers import (
    TIERS,
    annual_discount_pct,
    get_all_tiers,
    get_tier,
    get_tier_features,
    get_tier_level,
    tier_has_access,
)
from src.exceptions import ForbiddenError
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# TIER_HIERARCHY tests
# ---------------------------------------------------------------------------


class TestTierHierarchy:
    """TIER_HIERARCHY ordering and level lookups."""

    def test_hierarchy_order(self):
        assert TIER_HIERARCHY == ["free", "family", "family_plus", "school", "enterprise"]

    def test_free_is_level_0(self):
        assert get_tier_level("free") == 0

    def test_family_is_level_1(self):
        assert get_tier_level("family") == 1

    def test_family_plus_is_level_2(self):
        assert get_tier_level("family_plus") == 2

    def test_school_is_level_3(self):
        assert get_tier_level("school") == 3

    def test_enterprise_is_level_4(self):
        assert get_tier_level("enterprise") == 4

    def test_unknown_tier_defaults_to_level_0(self):
        assert get_tier_level("nonexistent") == 0

    def test_five_tiers_in_hierarchy(self):
        assert len(TIER_HIERARCHY) == 5


# ---------------------------------------------------------------------------
# tier_has_access tests
# ---------------------------------------------------------------------------


class TestTierHasAccess:
    """tier_has_access comparison logic."""

    def test_same_tier_has_access(self):
        assert tier_has_access("family", "family") is True

    def test_higher_tier_has_access(self):
        assert tier_has_access("family_plus", "family") is True

    def test_enterprise_has_access_to_all(self):
        for tier in TIER_HIERARCHY:
            assert tier_has_access("enterprise", tier) is True

    def test_free_denied_family_feature(self):
        assert tier_has_access("free", "family") is False

    def test_family_denied_family_plus_feature(self):
        assert tier_has_access("family", "family_plus") is False

    def test_family_plus_denied_school_feature(self):
        assert tier_has_access("family_plus", "school") is False

    def test_unknown_tier_denied_any_paid(self):
        assert tier_has_access("unknown", "family") is False


# ---------------------------------------------------------------------------
# get_tier_features (inheritance resolution) tests
# ---------------------------------------------------------------------------


class TestGetTierFeatures:
    """Feature inheritance resolution via *parent notation."""

    def test_free_has_extension_monitoring(self):
        assert "extension_monitoring" in get_tier_features("free")

    def test_family_has_real_time_alerts(self):
        assert "real_time_alerts" in get_tier_features("family")

    def test_family_plus_inherits_family_features(self):
        family_plus = get_tier_features("family_plus")
        # All family features should be present
        for f in get_tier_features("family"):
            assert f in family_plus

    def test_family_plus_has_location_tracking(self):
        assert "location_tracking" in get_tier_features("family_plus")

    def test_family_plus_has_screen_time(self):
        assert "screen_time" in get_tier_features("family_plus")

    def test_family_plus_has_creative_tools(self):
        assert "creative_tools" in get_tier_features("family_plus")

    def test_school_inherits_family_features(self):
        school = get_tier_features("school")
        for f in get_tier_features("family"):
            assert f in school

    def test_school_has_api_access(self):
        assert "api_access" in get_tier_features("school")

    def test_enterprise_inherits_school_features(self):
        enterprise = get_tier_features("enterprise")
        for f in get_tier_features("school"):
            assert f in enterprise

    def test_enterprise_has_sso(self):
        assert "sso" in get_tier_features("enterprise")

    def test_features_are_deduplicated(self):
        features = get_tier_features("family_plus")
        assert len(features) == len(set(features))


# ---------------------------------------------------------------------------
# Annual discount math tests
# ---------------------------------------------------------------------------


class TestAnnualDiscount:
    """Annual pricing discount calculations."""

    def test_family_annual_is_cheaper_than_monthly(self):
        tier = get_tier("family")
        monthly_total = tier["price_monthly"] * 12
        assert tier["price_annual"] < monthly_total

    def test_family_plus_annual_is_cheaper_than_monthly(self):
        tier = get_tier("family_plus")
        monthly_total = tier["price_monthly"] * 12
        assert tier["price_annual"] < monthly_total

    def test_family_discount_approx_20_pct(self):
        pct = annual_discount_pct("family")
        # 9.99 * 12 = 119.88; 95.90 annual → ~20%
        assert 18.0 <= pct <= 22.0

    def test_family_plus_discount_approx_20_pct(self):
        pct = annual_discount_pct("family_plus")
        assert 18.0 <= pct <= 22.0

    def test_free_discount_is_zero(self):
        assert annual_discount_pct("free") == 0.0

    def test_enterprise_discount_is_zero(self):
        # Enterprise has no pricing set
        assert annual_discount_pct("enterprise") == 0.0


# ---------------------------------------------------------------------------
# get_all_tiers tests
# ---------------------------------------------------------------------------


class TestGetAllTiers:
    """get_all_tiers returns all five tiers."""

    def test_returns_five_tiers(self):
        tiers = get_all_tiers()
        assert len(tiers) == 5

    def test_includes_free(self):
        keys = [t["tier_key"] for t in get_all_tiers()]
        assert "free" in keys

    def test_includes_family_plus(self):
        keys = [t["tier_key"] for t in get_all_tiers()]
        assert "family_plus" in keys

    def test_each_tier_has_required_fields(self):
        for tier in get_all_tiers():
            assert "tier_key" in tier
            assert "name" in tier
            assert "price_monthly" in tier
            assert "features" in tier


# ---------------------------------------------------------------------------
# DB-backed check_tier_access tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckTierAccess:
    """check_tier_access programmatic tier check."""

    async def test_no_gate_allows_access(self, test_session):
        """Feature with no gate in DB is always allowed."""
        group, _ = await make_test_group(test_session)
        # No gate row — should not raise
        await check_tier_access(test_session, group.id, "ungated_feature")

    async def test_free_user_blocked_by_family_gate(self, test_session):
        """Free-tier user blocked from family-gated feature."""
        group, _ = await make_test_group(test_session)
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_reports",
            required_tier="family",
        )
        test_session.add(gate)
        await test_session.flush()

        with pytest.raises(ForbiddenError):
            await check_tier_access(test_session, group.id, "test_reports")

    async def test_family_user_allowed_family_gate(self, test_session):
        """Family-tier user allowed through family-gated feature."""
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="active",
        )
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_blocking",
            required_tier="family",
        )
        test_session.add(sub)
        test_session.add(gate)
        await test_session.flush()

        # Should not raise
        await check_tier_access(test_session, group.id, "test_blocking")

    async def test_family_user_blocked_by_family_plus_gate(self, test_session):
        """Family-tier user blocked from family_plus-gated feature."""
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="active",
        )
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_location",
            required_tier="family_plus",
        )
        test_session.add(sub)
        test_session.add(gate)
        await test_session.flush()

        with pytest.raises(ForbiddenError):
            await check_tier_access(test_session, group.id, "test_location")

    async def test_school_user_allowed_family_plus_gate(self, test_session):
        """School-tier user meets or exceeds family_plus requirement."""
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="school",
            billing_cycle="monthly",
            status="active",
        )
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_screen_time",
            required_tier="family_plus",
        )
        test_session.add(sub)
        test_session.add(gate)
        await test_session.flush()

        # Should not raise
        await check_tier_access(test_session, group.id, "test_screen_time")

    async def test_no_subscription_treated_as_free(self, test_session):
        """User with no subscription row defaults to free tier."""
        group, _ = await make_test_group(test_session)
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_api_access",
            required_tier="school",
        )
        test_session.add(gate)
        await test_session.flush()

        with pytest.raises(ForbiddenError):
            await check_tier_access(test_session, group.id, "test_api_access")

    async def test_enterprise_allowed_all_gates(self, test_session):
        """Enterprise user passes any gate."""
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="enterprise",
            billing_cycle="annual",
            status="active",
        )
        gate = FeatureGate(
            id=uuid4(),
            feature_key="test_custom_compliance",
            required_tier="enterprise",
        )
        test_session.add(sub)
        test_session.add(gate)
        await test_session.flush()

        await check_tier_access(test_session, group.id, "test_custom_compliance")
