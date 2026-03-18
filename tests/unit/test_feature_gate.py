"""Unit tests for feature gating."""

import pytest
import pytest_asyncio

from tests.conftest import make_test_group
from src.billing.feature_gate import (
    get_plan_limits,
    is_feature_enabled,
    get_member_limit,
    get_platform_limit,
    get_group_plan,
    require_feature,
    get_feature_summary,
    PLAN_LIMITS,
)
from src.billing.models import Subscription
from src.exceptions import ForbiddenError
from uuid import uuid4


class TestPlanLimits:
    """Test static plan limit lookups."""

    def test_free_tier_has_1_member_limit(self):
        limits = get_plan_limits("free")
        assert limits["member_limit"] == 1

    def test_free_tier_has_3_platform_limit(self):
        limits = get_plan_limits("free")
        assert limits["platform_limit"] == 3

    def test_free_tier_basic_alerts_enabled(self):
        assert is_feature_enabled("free", "basic_alerts") is True

    def test_free_tier_pdf_reports_disabled(self):
        assert is_feature_enabled("free", "pdf_reports") is False

    def test_free_tier_spend_tracking_disabled(self):
        assert is_feature_enabled("free", "spend_tracking") is False

    def test_free_tier_blocking_disabled(self):
        assert is_feature_enabled("free", "blocking_rules") is False

    def test_family_tier_has_5_member_limit(self):
        assert get_member_limit("family") == 5

    def test_family_tier_has_10_platform_limit(self):
        assert get_platform_limit("family") == 10

    def test_family_tier_pdf_reports_enabled(self):
        assert is_feature_enabled("family", "pdf_reports") is True

    def test_family_tier_spend_tracking_enabled(self):
        assert is_feature_enabled("family", "spend_tracking") is True

    def test_school_tier_sis_enabled(self):
        assert is_feature_enabled("school", "sis_integration") is True

    def test_school_tier_sso_enabled(self):
        assert is_feature_enabled("school", "sso") is True

    def test_enterprise_unlimited_members(self):
        assert get_member_limit("enterprise") is None

    def test_enterprise_unlimited_platforms(self):
        assert get_platform_limit("enterprise") is None

    def test_enterprise_custom_taxonomy_enabled(self):
        assert is_feature_enabled("enterprise", "custom_taxonomy") is True

    def test_unknown_plan_returns_free(self):
        limits = get_plan_limits("nonexistent")
        assert limits["member_limit"] == 1

    def test_unknown_feature_returns_false(self):
        assert is_feature_enabled("family", "nonexistent_feature") is False

    def test_trialing_gets_family_features(self):
        assert is_feature_enabled("trialing", "pdf_reports") is True
        assert is_feature_enabled("trialing", "spend_tracking") is True

    def test_all_plans_have_basic_alerts(self):
        for plan in PLAN_LIMITS:
            assert is_feature_enabled(plan, "basic_alerts") is True


@pytest.mark.asyncio
class TestGetGroupPlan:
    """Test dynamic plan resolution from DB."""

    async def test_no_subscription_returns_free(self, test_session):
        group, _ = await make_test_group(test_session)
        plan = await get_group_plan(test_session, group.id)
        assert plan == "free"

    async def test_active_subscription_returns_plan(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="active",
        )
        test_session.add(sub)
        await test_session.flush()
        plan = await get_group_plan(test_session, group.id)
        assert plan == "family"

    async def test_trialing_returns_trialing(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="trialing",
        )
        test_session.add(sub)
        await test_session.flush()
        plan = await get_group_plan(test_session, group.id)
        assert plan == "trialing"

    async def test_cancelled_returns_free(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="cancelled",
        )
        test_session.add(sub)
        await test_session.flush()
        plan = await get_group_plan(test_session, group.id)
        assert plan == "free"


@pytest.mark.asyncio
class TestRequireFeature:
    """Test feature requirement enforcement."""

    async def test_require_feature_raises_on_free_tier(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "pdf_reports")

    async def test_require_feature_passes_on_family(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(),
            group_id=group.id,
            plan_type="family",
            billing_cycle="monthly",
            status="active",
        )
        test_session.add(sub)
        await test_session.flush()
        # Should not raise
        await require_feature(test_session, group.id, "pdf_reports")

    async def test_require_basic_alerts_passes_on_free(self, test_session):
        group, _ = await make_test_group(test_session)
        # basic_alerts is available on free tier
        await require_feature(test_session, group.id, "basic_alerts")


@pytest.mark.asyncio
class TestFeatureSummary:
    """Test feature summary endpoint logic."""

    async def test_summary_includes_all_fields(self, test_session):
        group, _ = await make_test_group(test_session)
        summary = await get_feature_summary(test_session, group.id)
        assert "plan" in summary
        assert "member_limit" in summary
        assert "platform_limit" in summary
        assert "features" in summary
        assert isinstance(summary["features"], dict)

    async def test_free_summary(self, test_session):
        group, _ = await make_test_group(test_session)
        summary = await get_feature_summary(test_session, group.id)
        assert summary["plan"] == "free"
        assert summary["member_limit"] == 1
        assert summary["platform_limit"] == 3
