"""Unit tests for persistent threshold alert tracking."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.billing.models import BudgetThreshold, FiredThresholdAlert, LLMAccount, SpendRecord
from src.billing.threshold_checker import check_thresholds, reset_fired_alerts
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_threshold_fires_once_per_period(test_session):
    """Same threshold+level should only fire once per billing period."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    account = LLMAccount(id=uuid4(), group_id=group.id, provider="openai", status="active")
    test_session.add(account)

    threshold = BudgetThreshold(
        id=uuid4(), group_id=group.id,
        type="soft", amount=100.0, currency="USD", notify_at=[50],
    )
    test_session.add(threshold)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spend = SpendRecord(
        id=uuid4(), group_id=group.id, llm_account_id=account.id,
        amount=60.0, currency="USD",
        period_start=month_start, period_end=now,
    )
    test_session.add(spend)
    await test_session.flush()

    # First check: should fire
    alerts = await check_thresholds(test_session, group.id)
    assert alerts == 1

    # Second check: should NOT fire again (persisted in DB)
    alerts2 = await check_thresholds(test_session, group.id)
    assert alerts2 == 0


@pytest.mark.asyncio
async def test_fired_alerts_persist_in_db(test_session):
    """FiredThresholdAlert rows should exist in DB after check."""
    from sqlalchemy import select

    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    account = LLMAccount(id=uuid4(), group_id=group.id, provider="openai", status="active")
    test_session.add(account)

    threshold = BudgetThreshold(
        id=uuid4(), group_id=group.id,
        type="hard", amount=50.0, currency="USD", notify_at=[80],
    )
    test_session.add(threshold)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spend = SpendRecord(
        id=uuid4(), group_id=group.id, llm_account_id=account.id,
        amount=45.0, currency="USD",
        period_start=month_start, period_end=now,
    )
    test_session.add(spend)
    await test_session.flush()

    await check_thresholds(test_session, group.id)

    result = await test_session.execute(
        select(FiredThresholdAlert).where(
            FiredThresholdAlert.threshold_id == threshold.id
        )
    )
    fired = list(result.scalars().all())
    assert len(fired) == 1
    assert fired[0].percentage_level == 80


@pytest.mark.asyncio
async def test_reset_fired_alerts(test_session):
    """reset_fired_alerts should clear all records."""
    from sqlalchemy import select

    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    account = LLMAccount(id=uuid4(), group_id=group.id, provider="openai", status="active")
    test_session.add(account)

    threshold = BudgetThreshold(
        id=uuid4(), group_id=group.id,
        type="soft", amount=100.0, currency="USD", notify_at=[50],
    )
    test_session.add(threshold)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spend = SpendRecord(
        id=uuid4(), group_id=group.id, llm_account_id=account.id,
        amount=60.0, currency="USD",
        period_start=month_start, period_end=now,
    )
    test_session.add(spend)
    await test_session.flush()

    await check_thresholds(test_session, group.id)

    # Reset
    await reset_fired_alerts(test_session)

    result = await test_session.execute(select(FiredThresholdAlert))
    assert len(list(result.scalars().all())) == 0

    # Should fire again after reset
    alerts = await check_thresholds(test_session, group.id)
    assert alerts == 1
