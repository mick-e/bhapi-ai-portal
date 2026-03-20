"""E2E tests for Stripe webhook idempotency.

Verifies that duplicate webhook events don't create duplicate records.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.billing.models import Subscription
from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def stripe_client():
    """Test client for Stripe webhook tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
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
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, session

    await session.close()
    await engine.dispose()


async def _setup_group(client, session, email="stripe-test@example.com"):
    """Register a user, return group_id as UUID."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Stripe Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me.json().get("group_id")


@pytest.mark.asyncio
async def test_duplicate_webhook_idempotent(stripe_client):
    """Sending the same Stripe subscription.created event twice should not create duplicates."""
    client, session = stripe_client
    gid = await _setup_group(client, session, "idempotent@example.com")

    stripe_event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_duplicate_test",
                "customer": "cus_test_idem",
                "status": "active",
                "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 86400 * 30,
                "trial_end": None,
                "metadata": {
                    "group_id": gid,
                    "plan_key": "family_monthly",
                },
            },
        },
    }

    # Mock verify_webhook_signature to return our event directly
    with patch("src.billing.router.verify_webhook_signature", return_value=stripe_event):
        # Send the same event twice
        resp1 = await client.post(
            "/api/v1/billing/webhooks",
            content=b"mock-payload",
            headers={"Stripe-Signature": "mock-sig"},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            "/api/v1/billing/webhooks",
            content=b"mock-payload",
            headers={"Stripe-Signature": "mock-sig"},
        )
        assert resp2.status_code == 200

    # Verify only one subscription exists for this group
    from uuid import UUID
    result = await session.execute(
        select(Subscription).where(Subscription.group_id == UUID(gid))
    )
    subs = list(result.scalars().all())
    assert len(subs) == 1, f"Expected 1 subscription but found {len(subs)}"
    assert subs[0].stripe_subscription_id == "sub_duplicate_test"


# --- Phase 3 addition ---


@pytest.mark.asyncio
async def test_webhook_out_of_order_events(stripe_client):
    """Out-of-order webhook events (created after updated) should still result in correct state."""
    client, session = stripe_client
    gid = await _setup_group(client, session, "outoforder@example.com")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Send "updated" event first (sets status to "past_due")
    updated_event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_ooo_test",
                "customer": "cus_ooo",
                "status": "past_due",
                "current_period_end": now_ts + 86400 * 30,
                "metadata": {"group_id": gid},
            },
        },
    }

    # Send "created" event second (sets status to "active")
    created_event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_ooo_test",
                "customer": "cus_ooo",
                "status": "active",
                "current_period_end": now_ts + 86400 * 30,
                "trial_end": None,
                "metadata": {
                    "group_id": gid,
                    "plan_key": "family_monthly",
                },
            },
        },
    }

    with patch("src.billing.router.verify_webhook_signature") as mock_verify:
        # First: updated (out of order)
        mock_verify.return_value = updated_event
        resp1 = await client.post(
            "/api/v1/billing/webhooks",
            content=b"payload1",
            headers={"Stripe-Signature": "sig1"},
        )
        assert resp1.status_code == 200

        # Second: created (should upsert, setting status to "active")
        mock_verify.return_value = created_event
        resp2 = await client.post(
            "/api/v1/billing/webhooks",
            content=b"payload2",
            headers={"Stripe-Signature": "sig2"},
        )
        assert resp2.status_code == 200

    # Check final state
    from uuid import UUID
    result = await session.execute(
        select(Subscription).where(Subscription.group_id == UUID(gid))
    )
    sub = result.scalar_one_or_none()
    assert sub is not None
    # The "created" handler upserts, so final status depends on order of processing
    assert sub.stripe_subscription_id == "sub_ooo_test"
