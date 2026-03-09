"""Unit tests for trial status computation."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.billing.models import Subscription
from src.billing.trial import FREE_TRIAL_DAYS, get_trial_status
from tests.conftest import make_test_group


@pytest_asyncio.fixture
async def fresh_group(test_session):
    """Create a group that was just created (full 14-day trial)."""
    group, owner_id = await make_test_group(test_session, name="Fresh Group")
    await test_session.commit()
    return group


@pytest_asyncio.fixture
async def expired_group(test_session):
    """Create a group whose trial has expired."""
    group, owner_id = await make_test_group(test_session, name="Expired Group")
    # Backdate created_at to 20 days ago
    group.created_at = datetime.now(timezone.utc) - timedelta(days=20)
    await test_session.flush()
    await test_session.commit()
    return group


@pytest_asyncio.fixture
async def almost_expired_group(test_session):
    """Create a group with ~2 days remaining (safe from clock drift)."""
    group, owner_id = await make_test_group(test_session, name="Almost Expired")
    group.created_at = datetime.now(timezone.utc) - timedelta(days=FREE_TRIAL_DAYS - 2)
    await test_session.flush()
    await test_session.commit()
    return group


class TestTrialStatus:
    @pytest.mark.asyncio
    async def test_fresh_group_has_14_days(self, test_session, fresh_group):
        status = await get_trial_status(test_session, fresh_group.id)
        assert status.is_active is True
        assert status.is_trial is True
        assert status.is_locked is False
        assert status.days_remaining >= 13  # allow for clock drift
        assert status.plan == "free"
        assert status.trial_end is not None

    @pytest.mark.asyncio
    async def test_expired_group_is_locked(self, test_session, expired_group):
        status = await get_trial_status(test_session, expired_group.id)
        assert status.is_active is False
        assert status.is_trial is True
        assert status.is_locked is True
        assert status.days_remaining == 0
        assert status.plan == "free"

    @pytest.mark.asyncio
    async def test_almost_expired(self, test_session, almost_expired_group):
        status = await get_trial_status(test_session, almost_expired_group.id)
        assert status.is_active is True
        assert status.is_trial is True
        assert status.is_locked is False
        assert status.days_remaining in (1, 2)  # depends on time of day

    @pytest.mark.asyncio
    async def test_active_subscription_overrides_trial(self, test_session, expired_group):
        """Paid subscription means trial doesn't matter."""
        sub = Subscription(
            id=uuid4(),
            group_id=expired_group.id,
            plan_type="family",
            status="active",
            billing_cycle="monthly",
        )
        test_session.add(sub)
        await test_session.flush()

        status = await get_trial_status(test_session, expired_group.id)
        assert status.is_active is True
        assert status.is_trial is False
        assert status.is_locked is False
        assert status.plan == "family"

    @pytest.mark.asyncio
    async def test_extension_via_settings(self, test_session, expired_group):
        """trial_extended_until extends the trial beyond 14 days."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        expired_group.settings = {"trial_extended_until": future.isoformat()}
        await test_session.flush()

        status = await get_trial_status(test_session, expired_group.id)
        assert status.is_active is True
        assert status.is_trial is True
        assert status.is_locked is False
        assert status.days_remaining > 0

    @pytest.mark.asyncio
    async def test_nonexistent_group_raises(self, test_session):
        from src.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await get_trial_status(test_session, uuid4())

    @pytest.mark.asyncio
    async def test_five_days_past_expiry(self, test_session):
        """Group expired 5 days ago should show 0 days remaining."""
        group, _ = await make_test_group(test_session, name="Past Expired")
        group.created_at = datetime.now(timezone.utc) - timedelta(days=FREE_TRIAL_DAYS + 5)
        await test_session.flush()
        await test_session.commit()

        status = await get_trial_status(test_session, group.id)
        assert status.is_locked is True
        assert status.days_remaining == 0

    @pytest.mark.asyncio
    async def test_free_subscription_does_not_override(self, test_session, expired_group):
        """A 'free' plan subscription should NOT unlock expired trial."""
        sub = Subscription(
            id=uuid4(),
            group_id=expired_group.id,
            plan_type="free",
            status="active",
            billing_cycle="monthly",
        )
        test_session.add(sub)
        await test_session.flush()

        status = await get_trial_status(test_session, expired_group.id)
        assert status.is_locked is True
