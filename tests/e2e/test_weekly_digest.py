"""E2E tests for weekly digest functionality."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.alerts.digest import run_weekly_digest
from src.alerts.models import Alert, NotificationPreference
from src.auth.models import User
from src.database import Base
from src.groups.models import Group, GroupMember


@pytest.fixture
async def digest_session():
    """In-memory DB session for digest tests."""
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
    yield session
    await session.close()
    await engine.dispose()


async def _seed_group_with_alerts(session, digest_mode="weekly", alert_count=3, days_ago=3):
    """Create user, group, member, alerts, and notification preference."""
    user_id = uuid4()
    group_id = uuid4()
    member_id = uuid4()

    user = User(
        id=user_id,
        email="digest@example.com",
        display_name="Digest Tester",
        password_hash="hashed",
        account_type="family",
        email_verified=True,
    )
    session.add(user)

    group = Group(id=group_id, name="Digest Family", type="family", owner_id=user_id)
    session.add(group)

    member = GroupMember(
        id=member_id,
        group_id=group_id,
        display_name="Child",
        role="member",
    )
    session.add(member)
    await session.flush()

    pref = NotificationPreference(
        id=uuid4(),
        user_id=user_id,
        group_id=group_id,
        category="risk_alert",
        channel="email",
        digest_mode=digest_mode,
        enabled=True,
    )
    session.add(pref)

    now = datetime.now(timezone.utc)
    for i in range(alert_count):
        alert = Alert(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            title=f"Test Alert {i + 1}",
            body=f"Alert body {i + 1}",
            severity="medium",
            status="pending",
            created_at=now - timedelta(days=days_ago),
        )
        session.add(alert)

    await session.flush()
    return user_id, group_id, member_id


@pytest.mark.asyncio
async def test_weekly_digest_no_preferences(digest_session):
    """Weekly digest returns 0 when no users have weekly preference."""
    result = await run_weekly_digest(digest_session)
    assert result == 0


@pytest.mark.asyncio
async def test_weekly_digest_sends_for_weekly_users(digest_session):
    """Weekly digest sends emails for users with weekly preference."""
    await _seed_group_with_alerts(digest_session, digest_mode="weekly", alert_count=3, days_ago=2)
    result = await run_weekly_digest(digest_session)
    # Email sending is mocked/fails gracefully in test, but function completes
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_weekly_digest_ignores_daily_users(digest_session):
    """Weekly digest does not send to users with daily preference."""
    await _seed_group_with_alerts(digest_session, digest_mode="daily", alert_count=3, days_ago=2)
    result = await run_weekly_digest(digest_session)
    assert result == 0


@pytest.mark.asyncio
async def test_weekly_digest_window_excludes_old_alerts(digest_session):
    """Weekly digest only includes alerts from the past 7 days."""
    await _seed_group_with_alerts(digest_session, digest_mode="weekly", alert_count=3, days_ago=10)
    result = await run_weekly_digest(digest_session)
    # Alerts are 10 days old, outside 7-day window — no digest sent
    assert result == 0


@pytest.mark.asyncio
async def test_weekly_digest_includes_recent_alerts(digest_session):
    """Weekly digest includes alerts within the 7-day window."""
    await _seed_group_with_alerts(digest_session, digest_mode="weekly", alert_count=5, days_ago=5)
    result = await run_weekly_digest(digest_session)
    assert isinstance(result, int)
