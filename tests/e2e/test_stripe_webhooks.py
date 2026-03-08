"""E2E tests for Stripe webhook DB persistence."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.billing.models import Subscription
from src.billing.stripe_client import handle_webhook_event
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_webhook_creates_subscription(test_session):
    """subscription.created webhook should create a Subscription row."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    await test_session.flush()

    event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_456",
                "status": "active",
                "metadata": {
                    "group_id": str(group.id),
                    "plan_key": "family_monthly",
                },
                "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 86400 * 30,
            }
        },
    }

    result = await handle_webhook_event(event, test_session)
    assert result["action"] == "subscription_created"

    # Verify DB row was created
    from sqlalchemy import select
    sub_result = await test_session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_test_123")
    )
    sub = sub_result.scalar_one_or_none()
    assert sub is not None
    assert sub.status == "active"
    assert sub.stripe_customer_id == "cus_test_456"


@pytest.mark.asyncio
async def test_webhook_updates_subscription(test_session):
    """subscription.updated webhook should update existing Subscription."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")

    sub = Subscription(
        id=uuid4(), group_id=group.id,
        stripe_customer_id="cus_456", stripe_subscription_id="sub_789",
        plan_type="family", billing_cycle="monthly", status="active",
    )
    test_session.add(sub)
    await test_session.flush()

    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_789",
                "status": "past_due",
                "metadata": {"group_id": str(group.id)},
                "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 86400 * 30,
            }
        },
    }

    result = await handle_webhook_event(event, test_session)
    assert result["action"] == "subscription_updated"

    from sqlalchemy import select
    sub_result = await test_session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_789")
    )
    updated = sub_result.scalar_one()
    assert updated.status == "past_due"


@pytest.mark.asyncio
async def test_webhook_cancels_subscription(test_session):
    """subscription.deleted webhook should set status=cancelled."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")

    sub = Subscription(
        id=uuid4(), group_id=group.id,
        stripe_subscription_id="sub_cancel",
        plan_type="family", billing_cycle="monthly", status="active",
    )
    test_session.add(sub)
    await test_session.flush()

    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_cancel",
                "metadata": {"group_id": str(group.id)},
            }
        },
    }

    result = await handle_webhook_event(event, test_session)
    assert result["action"] == "subscription_cancelled"

    from sqlalchemy import select
    sub_result = await test_session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_cancel")
    )
    updated = sub_result.scalar_one()
    assert updated.status == "cancelled"


@pytest.mark.asyncio
async def test_webhook_payment_failed(test_session):
    """payment_failed webhook should set status=past_due."""
    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")

    sub = Subscription(
        id=uuid4(), group_id=group.id,
        stripe_subscription_id="sub_fail",
        plan_type="family", billing_cycle="monthly", status="active",
    )
    test_session.add(sub)
    await test_session.flush()

    event = {
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "inv_123",
                "customer": "cus_456",
                "subscription": "sub_fail",
                "amount_due": 999,
            }
        },
    }

    result = await handle_webhook_event(event, test_session)
    assert result["action"] == "payment_failed"

    from sqlalchemy import select
    sub_result = await test_session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == "sub_fail")
    )
    updated = sub_result.scalar_one()
    assert updated.status == "past_due"


@pytest.mark.asyncio
async def test_webhook_unhandled_event(test_session):
    """Unhandled webhook events should be ignored."""
    event = {"type": "customer.created", "data": {"object": {}}}
    result = await handle_webhook_event(event, test_session)
    assert result["action"] == "ignored"
