"""Unit tests for COPPA 2026 consent enforcement helpers."""

import pytest
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.compliance.coppa_2026 import (
    check_third_party_consent,
    check_push_notification_consent,
    get_degraded_providers,
    get_third_party_consents,
    update_third_party_consent,
    update_push_notification_consent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_session():
    """In-memory SQLite async session for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    yield session
    await session.close()
    await engine.dispose()


@pytest.fixture
async def sample_user(test_session):
    """Create a test user (group owner / parent)."""
    user = User(
        id=uuid4(),
        email=f"parent-{uuid4().hex[:8]}@example.com",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest.fixture
async def sample_group(test_session, sample_user):
    """Create a test family group owned by sample_user."""
    group = Group(
        id=uuid4(),
        name="Test Family",
        type="family",
        owner_id=sample_user.id,
        settings={},
    )
    test_session.add(group)
    await test_session.flush()
    return group


@pytest.fixture
async def sample_member(test_session, sample_group):
    """Create a child member in sample_group."""
    member = GroupMember(
        id=uuid4(),
        group_id=sample_group.id,
        user_id=None,  # child members may not have user_id
        role="member",
        display_name="Test Child",
    )
    test_session.add(member)
    await test_session.flush()
    return member


# ---------------------------------------------------------------------------
# check_third_party_consent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckThirdPartyConsent:
    """Tests for check_third_party_consent()."""

    async def test_returns_false_when_no_records(self, test_session, sample_group, sample_member):
        """No consent records -> returns False (deny by default)."""
        result = await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "sendgrid"
        )
        assert result is False

    async def test_returns_false_after_default_creation(self, test_session, sample_group, sample_member):
        """Auto-created defaults are consented=False -> returns False."""
        # Trigger default creation
        await get_third_party_consents(test_session, sample_group.id, sample_member.id)
        result = await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "sendgrid"
        )
        assert result is False

    async def test_returns_true_when_consented(self, test_session, sample_group, sample_member, sample_user):
        """Explicit consent -> returns True."""
        await update_third_party_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "sendgrid", True
        )
        result = await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "sendgrid"
        )
        assert result is True

    async def test_returns_false_after_withdrawal(self, test_session, sample_group, sample_member, sample_user):
        """Consent granted then withdrawn -> returns False."""
        await update_third_party_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "sendgrid", True
        )
        await update_third_party_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "sendgrid", False
        )
        result = await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "sendgrid"
        )
        assert result is False

    async def test_checks_specific_provider(self, test_session, sample_group, sample_member, sample_user):
        """Consent for sendgrid does not affect google_cloud_ai."""
        await update_third_party_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "sendgrid", True
        )
        assert await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "sendgrid"
        ) is True
        assert await check_third_party_consent(
            test_session, sample_group.id, sample_member.id, "google_cloud_ai"
        ) is False


# ---------------------------------------------------------------------------
# check_push_notification_consent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCheckPushNotificationConsent:
    """Tests for check_push_notification_consent()."""

    async def test_returns_false_when_no_records(self, test_session, sample_group, sample_member):
        """No push consent records -> returns False."""
        result = await check_push_notification_consent(
            test_session, sample_group.id, sample_member.id, "risk_alerts"
        )
        assert result is False

    async def test_returns_true_when_consented(self, test_session, sample_group, sample_member, sample_user):
        """Explicit push consent -> returns True."""
        await update_push_notification_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "risk_alerts", True
        )
        result = await check_push_notification_consent(
            test_session, sample_group.id, sample_member.id, "risk_alerts"
        )
        assert result is True

    async def test_returns_false_after_withdrawal(self, test_session, sample_group, sample_member, sample_user):
        """Push consent withdrawn -> returns False."""
        await update_push_notification_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "risk_alerts", True
        )
        await update_push_notification_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "risk_alerts", False
        )
        result = await check_push_notification_consent(
            test_session, sample_group.id, sample_member.id, "risk_alerts"
        )
        assert result is False


# ---------------------------------------------------------------------------
# get_degraded_providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetDegradedProviders:
    """Tests for get_degraded_providers()."""

    async def test_all_degraded_by_default(self, test_session, sample_group, sample_member):
        """All providers degraded when no consent given."""
        degraded = await get_degraded_providers(
            test_session, sample_group.id, sample_member.id
        )
        assert "sendgrid" in degraded
        assert "google_cloud_ai" in degraded
        assert "hive_sensity" in degraded

    async def test_consented_provider_not_degraded(self, test_session, sample_group, sample_member, sample_user):
        """Consented provider removed from degraded list."""
        # First trigger default creation for all providers
        await get_degraded_providers(test_session, sample_group.id, sample_member.id)
        # Then consent to sendgrid
        await update_third_party_consent(
            test_session, sample_group.id, sample_member.id, sample_user.id,
            "sendgrid", True
        )
        degraded = await get_degraded_providers(
            test_session, sample_group.id, sample_member.id
        )
        assert "sendgrid" not in degraded
        assert "google_cloud_ai" in degraded
