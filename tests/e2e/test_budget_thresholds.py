"""End-to-end tests for budget threshold alerting and spend sync."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.auth.models import User
from src.billing.models import BudgetThreshold, LLMAccount, SpendRecord
from src.billing.threshold_checker import check_thresholds, reset_fired_alerts
from src.groups.models import Group, GroupMember


@pytest_asyncio.fixture
async def group_with_billing(test_session: AsyncSession):
    """Create a group with an LLM account and budget threshold."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Billing Admin",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Budget Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=user.id,
        role="parent",
        display_name="Billing Admin",
    )
    test_session.add(member)
    await test_session.flush()

    account = LLMAccount(
        id=uuid.uuid4(),
        group_id=group.id,
        provider="openai",
        credentials_encrypted="sk-test-key-123",
        status="active",
    )
    test_session.add(account)
    await test_session.flush()

    return group, member, user, account


class TestBudgetThresholdAlerting:
    @pytest.fixture(autouse=True)
    async def _reset_fired(self, test_session):
        await reset_fired_alerts(test_session)

    @pytest.mark.asyncio
    async def test_no_thresholds_no_alerts(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing
        count = await check_thresholds(test_session, group.id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_under_budget_no_alerts(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing

        # Set $100 budget
        threshold = BudgetThreshold(
            id=uuid.uuid4(),
            group_id=group.id,
            type="soft",
            amount=100.0,
            currency="USD",
            notify_at=[50, 80, 100],
        )
        test_session.add(threshold)

        # Add $20 of spend (under 50% threshold)
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            period_start=month_start,
            period_end=now,
            amount=20.0,
            currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        count = await check_thresholds(test_session, group.id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_50_percent_triggers_alert(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing

        threshold = BudgetThreshold(
            id=uuid.uuid4(),
            group_id=group.id,
            type="soft",
            amount=100.0,
            currency="USD",
            notify_at=[50, 80, 100],
        )
        test_session.add(threshold)

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            period_start=month_start,
            period_end=now,
            amount=55.0,
            currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        count = await check_thresholds(test_session, group.id)
        assert count == 1  # 50% alert

    @pytest.mark.asyncio
    async def test_100_percent_hard_threshold_high_severity(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing

        threshold = BudgetThreshold(
            id=uuid.uuid4(),
            group_id=group.id,
            type="hard",
            amount=50.0,
            currency="USD",
            notify_at=[100],
        )
        test_session.add(threshold)

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            period_start=month_start,
            period_end=now,
            amount=60.0,
            currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        count = await check_thresholds(test_session, group.id)
        assert count == 1

        # Check the alert was created with high severity
        alerts = (await test_session.execute(
            select(Alert).where(Alert.group_id == group.id)
        )).scalars().all()
        assert len(alerts) >= 1
        assert any(a.severity == "high" for a in alerts)

    @pytest.mark.asyncio
    async def test_duplicate_alerts_not_fired(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing

        threshold = BudgetThreshold(
            id=uuid.uuid4(),
            group_id=group.id,
            type="soft",
            amount=100.0,
            currency="USD",
            notify_at=[50],
        )
        test_session.add(threshold)

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            period_start=month_start,
            period_end=now,
            amount=60.0,
            currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        # First check
        count1 = await check_thresholds(test_session, group.id)
        assert count1 == 1

        # Second check — should not fire again
        count2 = await check_thresholds(test_session, group.id)
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_multiple_levels_fire(self, test_session, group_with_billing):
        group, member, user, account = group_with_billing

        threshold = BudgetThreshold(
            id=uuid.uuid4(),
            group_id=group.id,
            type="soft",
            amount=100.0,
            currency="USD",
            notify_at=[50, 80, 100],
        )
        test_session.add(threshold)

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            period_start=month_start,
            period_end=now,
            amount=105.0,  # Over 100%
            currency="USD",
        )
        test_session.add(record)
        await test_session.flush()

        count = await check_thresholds(test_session, group.id)
        assert count == 3  # 50%, 80%, 100% all fire
