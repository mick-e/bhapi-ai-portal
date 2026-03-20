"""E2E tests for trial enforcement on protected endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.billing.models import Subscription
from src.billing.trial import get_trial_status
from src.exceptions import TrialExpiredError
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_new_group_has_active_trial(test_session):
    """A freshly created group should have an active trial with ~14 days."""
    group, _ = await make_test_group(test_session, name="New Family")
    await test_session.commit()

    status = await get_trial_status(test_session, group.id)
    assert status.is_active is True
    assert status.is_trial is True
    assert status.is_locked is False
    assert status.days_remaining >= 13


@pytest.mark.asyncio
async def test_enforcement_allows_active_trial(test_session):
    """Enforcement dependency should pass for active trial."""
    from src.dependencies import require_active_trial_or_subscription
    from src.schemas import GroupContext

    group, owner_id = await make_test_group(test_session, name="Active Trial")
    await test_session.commit()

    auth = GroupContext(user_id=owner_id, group_id=group.id, role="parent")
    # Should not raise
    result = await require_active_trial_or_subscription(auth, test_session)
    assert result.group_id == group.id


@pytest.mark.asyncio
async def test_enforcement_blocks_expired_trial(test_session):
    """Enforcement dependency should raise TrialExpiredError for expired trial."""
    from src.dependencies import require_active_trial_or_subscription
    from src.schemas import GroupContext

    group, owner_id = await make_test_group(test_session, name="Expired Trial")
    group.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    await test_session.flush()
    await test_session.commit()

    auth = GroupContext(user_id=owner_id, group_id=group.id, role="parent")
    with pytest.raises(TrialExpiredError) as exc_info:
        await require_active_trial_or_subscription(auth, test_session)
    assert exc_info.value.code == "TRIAL_EXPIRED"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_paid_subscription_unlocks_expired_trial(test_session):
    """Paid subscription should override expired trial."""
    from src.dependencies import require_active_trial_or_subscription
    from src.schemas import GroupContext

    group, owner_id = await make_test_group(test_session, name="Paid Group")
    group.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    await test_session.flush()

    sub = Subscription(
        id=uuid4(),
        group_id=group.id,
        plan_type="family",
        status="active",
        billing_cycle="monthly",
    )
    test_session.add(sub)
    await test_session.flush()
    await test_session.commit()

    auth = GroupContext(user_id=owner_id, group_id=group.id, role="parent")
    result = await require_active_trial_or_subscription(auth, test_session)
    assert result.group_id == group.id


@pytest.mark.asyncio
async def test_trial_status_endpoint_schema(test_session):
    """Trial status response should have all expected fields."""
    group, _ = await make_test_group(test_session, name="Schema Test")
    await test_session.commit()

    status = await get_trial_status(test_session, group.id)
    assert hasattr(status, "is_active")
    assert hasattr(status, "is_trial")
    assert hasattr(status, "is_locked")
    assert hasattr(status, "days_remaining")
    assert hasattr(status, "trial_end")
    assert hasattr(status, "plan")
    assert hasattr(status, "contact_email")
    assert status.contact_email == "contactus@bhapi.io"


@pytest.mark.asyncio
async def test_group_settings_includes_trial_fields(test_session):
    """Portal group settings should include trial fields."""
    from src.portal.service import get_group_settings

    group, owner_id = await make_test_group(test_session, name="Settings Test")
    await test_session.commit()

    settings = await get_group_settings(test_session, group.id, owner_id)
    assert hasattr(settings, "trial_active")
    assert hasattr(settings, "trial_days_remaining")
    assert hasattr(settings, "trial_end")
    assert hasattr(settings, "trial_locked")
    assert settings.trial_active is True
    assert settings.trial_locked is False
