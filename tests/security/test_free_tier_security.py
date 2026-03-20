"""Security tests for free tier feature gating."""

from uuid import uuid4

import pytest

from src.billing.feature_gate import get_group_plan, require_feature
from src.billing.models import Subscription
from src.exceptions import ForbiddenError
from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestFreeTierSecurity:
    """Verify free tier users cannot access paid features."""

    async def test_free_user_cannot_access_pdf_reports(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "pdf_reports")

    async def test_free_user_cannot_access_csv_reports(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "csv_reports")

    async def test_free_user_cannot_access_spend_tracking(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "spend_tracking")

    async def test_free_user_cannot_access_blocking(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "blocking_rules")

    async def test_free_user_cannot_access_sis(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "sis_integration")

    async def test_free_user_cannot_access_sso(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "sso")

    async def test_free_user_cannot_access_api_keys(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "api_keys")

    async def test_free_user_cannot_access_webhooks(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "webhooks")

    async def test_family_user_cannot_access_sis(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="active",
        )
        test_session.add(sub)
        await test_session.flush()
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "sis_integration")

    async def test_family_user_cannot_access_custom_taxonomy(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="active",
        )
        test_session.add(sub)
        await test_session.flush()
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "custom_taxonomy")

    async def test_school_user_cannot_access_custom_taxonomy(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="school",
            billing_cycle="monthly", status="active",
        )
        test_session.add(sub)
        await test_session.flush()
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "custom_taxonomy")

    async def test_expired_subscription_reverts_to_free(self, test_session):
        group, _ = await make_test_group(test_session)
        sub = Subscription(
            id=uuid4(), group_id=group.id, plan_type="family",
            billing_cycle="monthly", status="cancelled",
        )
        test_session.add(sub)
        await test_session.flush()
        plan = await get_group_plan(test_session, group.id)
        assert plan == "free"
        with pytest.raises(ForbiddenError):
            await require_feature(test_session, group.id, "pdf_reports")
