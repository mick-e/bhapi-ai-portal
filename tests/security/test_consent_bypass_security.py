"""Security tests: verify consent enforcement cannot be bypassed.

These tests ensure that third-party consent defaults to denied,
that withdrawal is permanent until explicitly re-granted, that consent
is scoped to individual members, and that the risk pipeline respects
consent degradation.
"""

from uuid import uuid4

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


FAKE_UUID = "00000000-0000-0000-0000-000000000000"


async def _register_and_add_member(client: AsyncClient) -> tuple[str, str, str]:
    """Register a family account and add a child member.

    Returns (token, group_id, member_id).
    """
    resp = await client.post("/api/v1/auth/register", json={
        "email": f"parent-{uuid4().hex[:8]}@example.com",
        "password": "SecurePass1",
        "display_name": "Test Parent",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    token = data["access_token"]
    group_id = data["user"]["group_id"]

    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"display_name": "Test Child", "role": "member"},
        headers=headers,
    )
    assert resp.status_code == 201
    member_id = resp.json()["id"]

    return token, group_id, member_id


# ---------------------------------------------------------------------------
# Default consent bypass prevention
# ---------------------------------------------------------------------------


class TestConsentDefaultsBypass:
    """Verify all third-party consents default to False and cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_sendgrid_defaults_to_false(self, client):
        """SendGrid consent defaults to False, cannot be bypassed."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        sendgrid = [i for i in items if i["provider_key"] == "sendgrid"]
        assert len(sendgrid) == 1
        assert sendgrid[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_google_cloud_ai_defaults_to_false(self, client):
        """Google Cloud AI consent defaults to False."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        google = [i for i in items if i["provider_key"] == "google_cloud_ai"]
        assert len(google) == 1
        assert google[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_hive_sensity_defaults_to_false(self, client):
        """Hive/Sensity consent defaults to False."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        hive = [i for i in items if i["provider_key"] == "hive_sensity"]
        assert len(hive) == 1
        assert hive[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_twilio_sms_defaults_to_false(self, client):
        """Twilio SMS consent defaults to False."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        twilio = [i for i in items if i["provider_key"] == "twilio_sms"]
        assert len(twilio) == 1
        assert twilio[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_yoti_defaults_to_false(self, client):
        """Yoti consent defaults to False."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        yoti = [i for i in items if i["provider_key"] == "yoti"]
        assert len(yoti) == 1
        assert yoti[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_all_providers_default_to_false(self, client):
        """Every known provider starts unconsented."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        assert len(items) >= 5
        for item in items:
            assert item["consented"] is False, (
                f"Provider {item['provider_key']} should default to unconsented"
            )


# ---------------------------------------------------------------------------
# Consent withdrawal permanence
# ---------------------------------------------------------------------------


class TestConsentWithdrawalPermanence:
    """Verify that withdrawn consent stays False until re-granted."""

    @pytest.mark.asyncio
    async def test_withdrawal_is_permanent_until_reconsented(self, client):
        """Once withdrawn, consent stays False until explicitly re-granted."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Initialise defaults
        await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )

        # Grant sendgrid consent
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "sendgrid", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["consented"] is True

        # Withdraw sendgrid consent
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "sendgrid", "consented": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["consented"] is False
        assert resp.json()["withdrawn_at"] is not None

        # Verify it stays False on re-read
        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        sendgrid = [i for i in items if i["provider_key"] == "sendgrid"]
        assert len(sendgrid) == 1
        assert sendgrid[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_push_consent_withdrawal_permanent(self, client):
        """Push notification consent withdrawal stays until re-granted."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Grant push consent
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
        assert resp.json()["consented"] is True

        # Withdraw
        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={
                "member_id": member_id,
                "notification_type": "risk_alerts",
                "consented": False,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["consented"] is False
        assert resp.json()["withdrawn_at"] is not None

        # Verify still False on re-read
        resp = await client.get(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        items = resp.json()
        risk_alerts = [i for i in items if i["notification_type"] == "risk_alerts"]
        assert len(risk_alerts) == 1
        assert risk_alerts[0]["consented"] is False


# ---------------------------------------------------------------------------
# Consent scoping (member isolation)
# ---------------------------------------------------------------------------


class TestConsentMemberScoping:
    """Verify consent is scoped per-member and does not leak across members."""

    @pytest.mark.asyncio
    async def test_consent_scoped_to_member(self, client):
        """Consent for one member does not affect another member in the same group."""
        token, group_id, member_id_1 = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Add a second member
        resp = await client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"display_name": "Second Child", "role": "member"},
            headers=headers,
        )
        assert resp.status_code == 201
        member_id_2 = resp.json()["id"]

        # Initialise consent defaults for both members
        await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id_1}",
            headers=headers,
        )
        await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id_2}",
            headers=headers,
        )

        # Grant sendgrid consent for member 1 only
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id_1}",
            json={"provider_key": "sendgrid", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["consented"] is True

        # Member 2 should still have sendgrid unconsented
        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id_2}",
            headers=headers,
        )
        items = resp.json()
        sendgrid_2 = [i for i in items if i["provider_key"] == "sendgrid"]
        assert len(sendgrid_2) == 1
        assert sendgrid_2[0]["consented"] is False

    @pytest.mark.asyncio
    async def test_push_consent_scoped_to_member(self, client):
        """Push notification consent for one member does not affect another."""
        token, group_id, member_id_1 = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Add second member
        resp = await client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"display_name": "Second Child", "role": "member"},
            headers=headers,
        )
        assert resp.status_code == 201
        member_id_2 = resp.json()["id"]

        # Grant push consent for member 1
        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={
                "member_id": member_id_1,
                "notification_type": "risk_alerts",
                "consented": True,
            },
            headers=headers,
        )
        assert resp.status_code == 200

        # Member 2 should have no push consents
        resp = await client.get(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}&member_id={member_id_2}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Pipeline consent degradation enforcement
# ---------------------------------------------------------------------------


class TestPipelineConsentDegradation:
    """Verify risk pipeline consent degradation cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_no_external_api_classifications_without_consent(self, client):
        """Pipeline consent degradation prevents external API classifications."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Ensure all consents default to False
        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        for item in resp.json():
            assert item["consented"] is False

        from uuid import UUID

        from src.risk.engine import process_event

        results = await process_event(
            capture_event_data={
                "content": "test content",
                "media_urls": ["https://example.com/img.jpg"],
            },
            group_id=UUID(group_id),
            member_id=UUID(member_id),
        )
        # No external API results should appear (Hive, Sensity)
        for r in results:
            assert "Hive" not in r.reasoning
            assert "Sensity" not in r.reasoning

    @pytest.mark.asyncio
    async def test_invalid_provider_consent_update_rejected(self, client):
        """Cannot grant consent to an unknown provider (potential bypass attempt)."""
        token, group_id, member_id = await _register_and_add_member(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={group_id}&member_id={member_id}",
            json={"provider_key": "malicious_provider", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Privacy notice enforcement
# ---------------------------------------------------------------------------


class TestPrivacyNoticeBypass:
    """Verify privacy notice acceptance cannot be bypassed during registration."""

    @pytest.mark.asyncio
    async def test_cannot_register_without_privacy_notice(self, client):
        """Registration endpoint rejects requests without privacy_notice_accepted."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "bypass@example.com",
            "password": "SecurePass1",
            "display_name": "Bypass User",
            "account_type": "family",
            "privacy_notice_accepted": False,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_cannot_register_omitting_privacy_notice(self, client):
        """Registration with privacy_notice_accepted omitted (defaults False) is rejected."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "omitted@example.com",
            "password": "SecurePass1",
            "display_name": "Omit User",
            "account_type": "family",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_consent_endpoints_require_auth(self, client):
        """Consent endpoints cannot be accessed without authentication."""
        # Third-party consent
        resp = await client.get(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}",
        )
        assert resp.status_code == 401

        # Update third-party consent
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}",
            json={"provider_key": "sendgrid", "consented": True},
        )
        assert resp.status_code == 401

        # Push consent
        resp = await client.get(
            f"/api/v1/compliance/coppa/push-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}",
        )
        assert resp.status_code == 401
