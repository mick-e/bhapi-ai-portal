"""COPPA 2026 security tests — auth enforcement, input validation, RBAC."""

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


class TestUnauthenticatedAccess:
    """All COPPA 2026 endpoints must require authentication."""

    ENDPOINTS = [
        ("GET", f"/api/v1/compliance/coppa/third-party-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}"),
        ("PUT", f"/api/v1/compliance/coppa/third-party-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}"),
        ("PUT", f"/api/v1/compliance/coppa/third-party-consent/bulk?group_id={FAKE_UUID}"),
        ("POST", f"/api/v1/compliance/coppa/refuse-partial-collection?group_id={FAKE_UUID}"),
        ("GET", f"/api/v1/compliance/coppa/retention?group_id={FAKE_UUID}"),
        ("PUT", f"/api/v1/compliance/coppa/retention?group_id={FAKE_UUID}"),
        ("GET", f"/api/v1/compliance/coppa/retention/disclosure?group_id={FAKE_UUID}"),
        ("GET", f"/api/v1/compliance/coppa/push-consent?group_id={FAKE_UUID}&member_id={FAKE_UUID}"),
        ("PUT", f"/api/v1/compliance/coppa/push-consent?group_id={FAKE_UUID}"),
        ("POST", f"/api/v1/compliance/coppa/video-verification?group_id={FAKE_UUID}"),
        ("GET", f"/api/v1/compliance/coppa/video-verification/{FAKE_UUID}"),
        ("PATCH", f"/api/v1/compliance/coppa/video-verification/{FAKE_UUID}?score=0.9"),
        ("GET", f"/api/v1/compliance/coppa/video-verifications?group_id={FAKE_UUID}"),
        ("GET", f"/api/v1/compliance/coppa/video-verification-status?group_id={FAKE_UUID}"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,url", ENDPOINTS)
    async def test_requires_auth(self, client, method, url):
        """Every COPPA 2026 endpoint returns 401 without auth."""
        body = {}
        if method == "PUT" and "third-party-consent" in url and "bulk" not in url:
            body = {"provider_key": "stripe", "consented": True}
        elif method == "PUT" and "bulk" in url:
            body = {"member_id": FAKE_UUID, "consents": []}
        elif method == "POST" and "refuse" in url:
            body = {"member_id": FAKE_UUID, "refuse_third_party_sharing": True}
        elif method == "PUT" and "retention" in url:
            body = {"data_type": "capture_events", "retention_days": 365, "auto_delete": True}
        elif method == "PUT" and "push-consent" in url:
            body = {"member_id": FAKE_UUID, "notification_type": "risk_alerts", "consented": True}
        elif method == "POST" and "video-verification" in url:
            body = {"verification_method": "video_selfie"}

        if method == "GET":
            resp = await client.get(url)
        elif method == "POST":
            resp = await client.post(url, json=body)
        elif method == "PUT":
            resp = await client.put(url, json=body)
        elif method == "PATCH":
            resp = await client.patch(url)
        else:
            pytest.fail(f"Unknown method: {method}")

        assert resp.status_code == 401, f"{method} {url} did not return 401"


class TestInputValidation:
    """Input validation on COPPA 2026 endpoints."""

    @pytest.fixture
    async def auth_headers(self, client):
        """Register and return auth headers."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "parent@example.com",
            "password": "SecurePass1",
            "display_name": "Test Parent",
            "account_type": "family",
        })
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}, resp.json()["user"]["group_id"]

    @pytest.mark.asyncio
    async def test_retention_days_too_low(self, client, auth_headers):
        """Retention days below schema minimum (30) rejected at validation level."""
        headers, group_id = auth_headers
        resp = await client.put(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            json={"data_type": "capture_events", "retention_days": 5, "auto_delete": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_retention_days_too_high(self, client, auth_headers):
        """Retention days above 3650 rejected."""
        headers, group_id = auth_headers
        resp = await client.put(
            f"/api/v1/compliance/coppa/retention?group_id={group_id}",
            json={"data_type": "capture_events", "retention_days": 5000, "auto_delete": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_push_consent_invalid_type(self, client, auth_headers):
        """Invalid notification type rejected by schema regex."""
        headers, group_id = auth_headers
        resp = await client.put(
            f"/api/v1/compliance/coppa/push-consent?group_id={group_id}",
            json={"member_id": FAKE_UUID, "notification_type": "spam", "consented": True},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_video_verification_invalid_method(self, client, auth_headers):
        """Invalid verification method rejected by schema regex."""
        headers, group_id = auth_headers
        resp = await client.post(
            f"/api/v1/compliance/coppa/video-verification?group_id={group_id}",
            json={"verification_method": "knowledge_based"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_video_score_out_of_range(self, client, auth_headers):
        """Score outside 0.0-1.0 rejected."""
        headers, group_id = auth_headers
        resp = await client.patch(
            f"/api/v1/compliance/coppa/video-verification/{FAKE_UUID}?score=1.5",
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_group_id(self, client, auth_headers):
        """Missing required group_id returns 422."""
        headers, _ = auth_headers
        resp = await client.get(
            "/api/v1/compliance/coppa/retention",
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_bulk_consents(self, client, auth_headers):
        """Empty consents array in bulk update is valid (no-op)."""
        headers, group_id = auth_headers
        resp = await client.put(
            f"/api/v1/compliance/coppa/third-party-consent/bulk?group_id={group_id}",
            json={"member_id": FAKE_UUID, "consents": []},
            headers=headers,
        )
        assert resp.status_code == 200
