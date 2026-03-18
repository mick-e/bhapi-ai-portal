"""COPPA 2026 compliance E2E tests.

Tests third-party consent, retention policies, push notification consent,
refuse-partial-collection, and video verification endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def client():
    """Test client with in-memory SQLite database."""
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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    await session.close()
    await engine.dispose()


async def _register_and_add_member(client: AsyncClient) -> tuple[str, str, str]:
    """Register a family account and add a child member. Returns (token, group_id, member_id)."""
    # Register parent
    resp = await client.post("/api/v1/auth/register", json={
        "email": "parent@example.com",
        "password": "SecurePass1",
        "display_name": "Test Parent",
        "account_type": "family",
    })
    assert resp.status_code == 201
    data = resp.json()
    token = data["access_token"]
    group_id = data["user"]["group_id"]

    headers = {"Authorization": f"Bearer {token}"}

    # Add child member via groups endpoint
    resp = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "display_name": "Test Child",
            "role": "member",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    member_id = resp.json()["id"]

    return token, group_id, member_id


# ---------------------------------------------------------------------------
# Third-party consent
# ---------------------------------------------------------------------------


class TestThirdPartyConsent:
    """Tests for per-third-party consent endpoints."""

    @pytest.mark.asyncio
    async def test_get_third_party_consents_creates_defaults(self, client):
        """First GET creates default consent items for all providers."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 5  # At least 5 known providers
        # All should be unconsented by default
        for item in items:
            assert item["consented"] is False
            assert item["provider_key"] in [
                "stripe", "sendgrid", "twilio_sms", "google_cloud_ai",
                "hive_sensity", "yoti", "render",
            ]

    @pytest.mark.asyncio
    async def test_update_single_consent(self, client):
        """Can consent to a single provider."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Get defaults first
        await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )

        # Consent to Stripe
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "stripe", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["consented"] is True
        assert data["provider_key"] == "stripe"
        assert data["consented_at"] is not None

    @pytest.mark.asyncio
    async def test_withdraw_consent(self, client):
        """Can withdraw previously given consent."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Consent then withdraw
        await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "sendgrid", "consented": True},
            headers=headers,
        )
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "sendgrid", "consented": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["consented"] is False
        assert data["withdrawn_at"] is not None

    @pytest.mark.asyncio
    async def test_invalid_provider_returns_422(self, client):
        """Unknown provider key returns validation error."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "unknown_provider", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_update_consent(self, client):
        """Bulk update multiple provider consents at once."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent/bulk?group_id={group_id}",
            json={
                "member_id": member_id,
                "consents": [
                    {"provider_key": "stripe", "consented": True},
                    {"provider_key": "render", "consented": True},
                    {"provider_key": "sendgrid", "consented": False},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3


# ---------------------------------------------------------------------------
# Refuse partial collection
# ---------------------------------------------------------------------------


class TestRefusePartialCollection:
    """Tests for refuse-partial-collection toggle."""

    @pytest.mark.asyncio
    async def test_refuse_withdraws_non_essential(self, client):
        """Refusing partial collection withdraws consent from non-essential providers."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # First consent to all
        for provider in ["stripe", "sendgrid", "google_cloud_ai", "render"]:
            await client.put(
                f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
                json={"provider_key": provider, "consented": True},
                headers=headers,
            )

        # Refuse partial collection
        resp = await client.post(
            f"/api/v1/compliance/coppa/refuse-partial-collection?group_id={group_id}",
            json={"member_id": member_id, "refuse_third_party_sharing": True},
            headers=headers,
        )
        assert resp.status_code == 200
        items = resp.json()

        # Essential providers (stripe, render) should keep consent
        essential = [i for i in items if i["provider_key"] in ("stripe", "render")]
        for e in essential:
            assert e["consented"] is True

        # Non-essential should be withdrawn
        non_essential = [i for i in items if i["provider_key"] not in ("stripe", "render")]
        for ne in non_essential:
            assert ne["consented"] is False


# ---------------------------------------------------------------------------
# Retention policies
# ---------------------------------------------------------------------------


class TestRetentionPolicies:
    """Tests for data retention policy endpoints."""

    @pytest.mark.asyncio
    async def test_get_creates_defaults(self, client):
        """First GET creates default retention policies."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        policies = resp.json()
        assert len(policies) >= 5
        data_types = [p["data_type"] for p in policies]
        assert "capture_events" in data_types
        assert "risk_events" in data_types
        assert "audit_entries" in data_types

    @pytest.mark.asyncio
    async def test_update_retention_days(self, client):
        """Can update retention period for a data type."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Get defaults first
        await client.get(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            headers=headers,
        )

        resp = await client.put(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            json={"data_type": "capture_events", "retention_days": 180, "auto_delete": True},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["retention_days"] == 180
        assert data["auto_delete"] is True

    @pytest.mark.asyncio
    async def test_below_minimum_rejected(self, client):
        """Cannot set retention below regulatory minimum."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        await client.get(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            headers=headers,
        )

        # audit_entries minimum is 1095 days (3 years)
        resp = await client.put(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            json={"data_type": "audit_entries", "retention_days": 30, "auto_delete": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_data_type_rejected(self, client):
        """Invalid data type returns validation error."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            json={"data_type": "invalid_type", "retention_days": 365, "auto_delete": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_retention_disclosure(self, client):
        """Can get parent-facing retention disclosure."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/retention/disclosure?group_id={group_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "policies" in data
        assert len(data["policies"]) >= 5


# ---------------------------------------------------------------------------
# Push notification consent
# ---------------------------------------------------------------------------


class TestPushNotificationConsent:
    """Tests for push notification consent endpoints."""

    @pytest.mark.asyncio
    async def test_get_empty_consents(self, client):
        """No consents returns empty list."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_grant_push_consent(self, client):
        """Can grant push notification consent."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={
                "member_id": member_id,
                "notification_type": "risk_alerts",
                "consented": True,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["consented"] is True
        assert data["notification_type"] == "risk_alerts"
        assert data["consented_at"] is not None

    @pytest.mark.asyncio
    async def test_withdraw_push_consent(self, client):
        """Can withdraw push notification consent."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Grant then withdraw
        await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={"member_id": member_id, "notification_type": "weekly_reports", "consented": True},
            headers=headers,
        )
        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={"member_id": member_id, "notification_type": "weekly_reports", "consented": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["consented"] is False
        assert data["withdrawn_at"] is not None

    @pytest.mark.asyncio
    async def test_invalid_notification_type_rejected(self, client):
        """Invalid notification type returns validation error."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={"member_id": member_id, "notification_type": "invalid_type", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_multiple_notification_types(self, client):
        """Can set different consents for different notification types."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        for ntype in ["risk_alerts", "activity_summaries", "weekly_reports"]:
            resp = await client.put(
                f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
                json={"member_id": member_id, "notification_type": ntype, "consented": True},
                headers=headers,
            )
            assert resp.status_code == 200

        resp = await client.get(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3


# ---------------------------------------------------------------------------
# Video verification
# ---------------------------------------------------------------------------


class TestVideoVerification:
    """Tests for video verification (enhanced VPC) endpoints."""

    @pytest.mark.asyncio
    async def test_initiate_video_selfie(self, client):
        """Can initiate video selfie verification."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["verification_method"] == "video_selfie"
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_initiate_yoti_id_check(self, client):
        """Can initiate Yoti ID check (may fail in test env but should create record)."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "yoti_id_check"},
            headers=headers,
        )
        # Should succeed (Yoti failure handled gracefully)
        assert resp.status_code == 201
        data = resp.json()
        assert data["verification_method"] == "yoti_id_check"

    @pytest.mark.asyncio
    async def test_invalid_method_rejected(self, client):
        """Invalid verification method returns validation error."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "phone_call"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_verification_status(self, client):
        """Can retrieve a verification by ID."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        vid = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/compliance/coppa/video-verification/{vid}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == vid

    @pytest.mark.asyncio
    async def test_complete_verification_success(self, client):
        """Can complete verification with passing score."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        vid = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{vid}?score=0.95",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "verified"
        assert data["verification_score"] == 0.95
        assert data["verified_at"] is not None

    @pytest.mark.asyncio
    async def test_complete_verification_failure(self, client):
        """Low score results in failed status."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        vid = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{vid}?score=0.3",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    @pytest.mark.asyncio
    async def test_verification_status_endpoint(self, client):
        """Can check if parent has valid verification."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Before any verification
        resp = await client.get(
            f"/api/v1/compliance/coppa/video-verification-status?group_id={group_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["has_valid_verification"] is False

        # Create and complete verification
        create_resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        vid = create_resp.json()["id"]
        await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{vid}?score=0.9",
            headers=headers,
        )

        resp = await client.get(
            f"/api/v1/compliance/coppa/video-verification-status?group_id={group_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["has_valid_verification"] is True

    @pytest.mark.asyncio
    async def test_list_verifications(self, client):
        """Can list all verifications for a parent."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create two verifications
        await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "yoti_id_check"},
            headers=headers,
        )

        resp = await client.get(
            f"/api/v1/compliance/coppa/video-verifications?group_id={group_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_cannot_complete_already_verified(self, client):
        """Cannot re-verify an already verified record."""
        token, group_id, _ = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "video_selfie"},
            headers=headers,
        )
        vid = create_resp.json()["id"]

        # Complete once
        await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{vid}?score=0.95",
            headers=headers,
        )
        # Try again
        resp = await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{vid}?score=0.99",
            headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth/403 tests
# ---------------------------------------------------------------------------


class TestCOPPA2026Auth:
    """Tests for authentication enforcement on COPPA 2026 endpoints."""

    @pytest.mark.asyncio
    async def test_third_party_consent_requires_auth(self, client):
        """Third-party consent endpoint requires authentication."""
        resp = await client.get(
            "/api/v1/compliance/coppa/third-party-consent?group_id=00000000-0000-0000-0000-000000000000&member_id=00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_retention_requires_auth(self, client):
        """Retention endpoint requires authentication."""
        resp = await client.get(
            "/api/v1/compliance/coppa/retention?group_id=00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_push_consent_requires_auth(self, client):
        """Push consent endpoint requires authentication."""
        resp = await client.get(
            "/api/v1/compliance/coppa/push-consent?group_id=00000000-0000-0000-0000-000000000000&member_id=00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_video_verification_requires_auth(self, client):
        """Video verification endpoint requires authentication."""
        resp = await client.post(
            "/api/v1/compliance/coppa/video-verification?group_id=00000000-0000-0000-0000-000000000000",
            json={"verification_method": "video_selfie"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verification_status_requires_auth(self, client):
        """Verification status endpoint requires authentication."""
        resp = await client.get(
            "/api/v1/compliance/coppa/video-verification-status?group_id=00000000-0000-0000-0000-000000000000",
        )
        assert resp.status_code == 401
