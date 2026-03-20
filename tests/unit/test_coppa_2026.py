"""COPPA 2026 unit tests — retention engine, consent logic, video verification."""

from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base


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


# ---------------------------------------------------------------------------
# Retention policy engine
# ---------------------------------------------------------------------------


class TestRetentionPolicyDefaults:
    """Tests for default retention policy creation."""

    @pytest.mark.asyncio
    async def test_creates_defaults_for_new_group(self, test_session):
        """get_retention_policies creates defaults when none exist."""
        from src.compliance.retention import get_retention_policies

        group_id = uuid4()
        policies = await get_retention_policies(test_session, group_id)
        assert len(policies) >= 5
        data_types = [p.data_type for p in policies]
        assert "capture_events" in data_types
        assert "risk_events" in data_types
        assert "audit_entries" in data_types

    @pytest.mark.asyncio
    async def test_default_retention_days(self, test_session):
        """Default retention is 365 days for most types, 1095 for audit."""
        from src.compliance.retention import get_retention_policies

        group_id = uuid4()
        policies = await get_retention_policies(test_session, group_id)
        policy_map = {p.data_type: p for p in policies}
        assert policy_map["capture_events"].retention_days == 365
        assert policy_map["audit_entries"].retention_days == 1095

    @pytest.mark.asyncio
    async def test_idempotent_get(self, test_session):
        """Calling get twice doesn't duplicate policies."""
        from src.compliance.retention import get_retention_policies

        group_id = uuid4()
        p1 = await get_retention_policies(test_session, group_id)
        await test_session.commit()
        p2 = await get_retention_policies(test_session, group_id)
        assert len(p1) == len(p2)


class TestRetentionPolicyUpdate:
    """Tests for retention policy updates."""

    @pytest.mark.asyncio
    async def test_update_retention_days(self, test_session):
        """Can update retention days for a data type."""
        from src.compliance.retention import get_retention_policies, update_retention_policy

        group_id = uuid4()
        await get_retention_policies(test_session, group_id)
        await test_session.commit()

        policy = await update_retention_policy(test_session, group_id, "capture_events", 180)
        assert policy.retention_days == 180

    @pytest.mark.asyncio
    async def test_reject_below_minimum(self, test_session):
        """Cannot set retention below regulatory minimum."""
        from src.compliance.retention import get_retention_policies, update_retention_policy
        from src.exceptions import ValidationError

        group_id = uuid4()
        await get_retention_policies(test_session, group_id)
        await test_session.commit()

        with pytest.raises(ValidationError):
            await update_retention_policy(test_session, group_id, "audit_entries", 30)

    @pytest.mark.asyncio
    async def test_reject_invalid_data_type(self, test_session):
        """Invalid data type raises ValidationError."""
        from src.compliance.retention import update_retention_policy
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await update_retention_policy(test_session, uuid4(), "invalid_type", 365)

    @pytest.mark.asyncio
    async def test_disable_auto_delete(self, test_session):
        """Can disable auto-delete."""
        from src.compliance.retention import get_retention_policies, update_retention_policy

        group_id = uuid4()
        await get_retention_policies(test_session, group_id)
        await test_session.commit()

        policy = await update_retention_policy(
            test_session, group_id, "alerts", 730, auto_delete=False
        )
        assert policy.auto_delete is False


class TestRetentionDisclosure:
    """Tests for parent-facing retention disclosure."""

    @pytest.mark.asyncio
    async def test_disclosure_structure(self, test_session):
        """Disclosure contains required fields."""
        from src.compliance.retention import get_retention_disclosure

        group_id = uuid4()
        disclosure = await get_retention_disclosure(test_session, group_id)
        assert "summary" in disclosure
        assert "policies" in disclosure
        assert "generated_at" in disclosure
        assert len(disclosure["policies"]) >= 5

    @pytest.mark.asyncio
    async def test_disclosure_includes_minimums(self, test_session):
        """Disclosure includes minimum allowed days for each type."""
        from src.compliance.retention import get_retention_disclosure

        group_id = uuid4()
        disclosure = await get_retention_disclosure(test_session, group_id)
        for policy in disclosure["policies"]:
            assert "minimum_allowed_days" in policy
            assert policy["minimum_allowed_days"] >= 30


# ---------------------------------------------------------------------------
# Third-party consent
# ---------------------------------------------------------------------------


class TestThirdPartyProviders:
    """Tests for third-party provider definitions."""

    def test_all_providers_defined(self):
        """All expected providers are defined."""
        from src.compliance.coppa_2026 import THIRD_PARTY_PROVIDERS

        keys = [p["provider_key"] for p in THIRD_PARTY_PROVIDERS]
        assert "stripe" in keys
        assert "sendgrid" in keys
        assert "google_cloud_ai" in keys
        assert "yoti" in keys
        assert "render" in keys

    def test_providers_have_required_fields(self):
        """Each provider has required fields."""
        from src.compliance.coppa_2026 import THIRD_PARTY_PROVIDERS

        for provider in THIRD_PARTY_PROVIDERS:
            assert "provider_key" in provider
            assert "provider_name" in provider
            assert "data_purpose" in provider
            assert len(provider["data_purpose"]) > 20  # Meaningful description


class TestNotificationTypes:
    """Tests for push notification type validation."""

    def test_valid_types(self):
        """All expected notification types are defined."""
        from src.compliance.coppa_2026 import NOTIFICATION_TYPES

        assert "risk_alerts" in NOTIFICATION_TYPES
        assert "activity_summaries" in NOTIFICATION_TYPES
        assert "weekly_reports" in NOTIFICATION_TYPES
        assert "all" in NOTIFICATION_TYPES


class TestVerificationMethods:
    """Tests for verification method definitions."""

    def test_valid_methods(self):
        """All expected verification methods are defined."""
        from src.compliance.coppa_2026 import VERIFICATION_METHODS

        assert "video_call" in VERIFICATION_METHODS
        assert "yoti_id_check" in VERIFICATION_METHODS
        assert "video_selfie" in VERIFICATION_METHODS

    def test_knowledge_based_removed(self):
        """Knowledge-based verification is NOT in the valid methods (COPPA 2026)."""
        from src.compliance.coppa_2026 import VERIFICATION_METHODS

        assert "knowledge_based" not in VERIFICATION_METHODS


# ---------------------------------------------------------------------------
# Video verification logic
# ---------------------------------------------------------------------------


class TestVideoVerificationLogic:
    """Tests for video verification business logic."""

    @pytest.mark.asyncio
    async def test_initiate_creates_record(self, test_session):
        """Initiating verification creates a pending record."""
        from src.compliance.coppa_2026 import initiate_video_verification

        group_id = uuid4()
        parent_id = uuid4()

        v = await initiate_video_verification(
            test_session, group_id, parent_id, "video_selfie"
        )
        assert v.status == "pending"
        assert v.verification_method == "video_selfie"
        assert v.expires_at is not None

    @pytest.mark.asyncio
    async def test_complete_with_high_score(self, test_session):
        """Score >= 0.7 results in verified status."""
        from src.compliance.coppa_2026 import (
            complete_video_verification,
            initiate_video_verification,
        )

        group_id = uuid4()
        parent_id = uuid4()

        v = await initiate_video_verification(
            test_session, group_id, parent_id, "video_selfie"
        )
        await test_session.commit()

        completed = await complete_video_verification(test_session, v.id, 0.85)
        assert completed.status == "verified"
        assert completed.verified_at is not None

    @pytest.mark.asyncio
    async def test_complete_with_low_score(self, test_session):
        """Score < 0.7 results in failed status."""
        from src.compliance.coppa_2026 import (
            complete_video_verification,
            initiate_video_verification,
        )

        group_id = uuid4()
        parent_id = uuid4()

        v = await initiate_video_verification(
            test_session, group_id, parent_id, "video_selfie"
        )
        await test_session.commit()

        completed = await complete_video_verification(test_session, v.id, 0.4)
        assert completed.status == "failed"

    @pytest.mark.asyncio
    async def test_has_valid_verification(self, test_session):
        """has_valid_video_verification returns True after successful verification."""
        from src.compliance.coppa_2026 import (
            complete_video_verification,
            has_valid_video_verification,
            initiate_video_verification,
        )

        group_id = uuid4()
        parent_id = uuid4()

        # Before
        assert await has_valid_video_verification(test_session, group_id, parent_id) is False

        v = await initiate_video_verification(
            test_session, group_id, parent_id, "video_selfie"
        )
        await test_session.commit()
        await complete_video_verification(test_session, v.id, 0.9)
        await test_session.commit()

        # After
        assert await has_valid_video_verification(test_session, group_id, parent_id) is True
