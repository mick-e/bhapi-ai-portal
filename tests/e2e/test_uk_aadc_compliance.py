"""E2E tests for UK AADC re-review compliance flow (Phase 4 Task 24).

Covers:
- Registration with country_code="GB" returns requires_aadc_consent=True
- POST /api/v1/compliance/uk-aadc/consent records the consent
- GET  /api/v1/compliance/uk-aadc/status reflects current state
- Stale consent versions are rejected
- Refused consent is rejected
- Existing privacy defaults already enforce geolocation OFF for under-18
  (validated against get_default_privacy_settings)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.compliance.uk_aadc import get_default_privacy_settings
from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def override_get_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, session

    await session.close()
    await engine.dispose()


async def _register(ac, email, country_code=None):
    payload = {
        "email": email,
        "password": "SecurePass1",
        "display_name": "AADC Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    }
    if country_code:
        payload["country_code"] = country_code
    resp = await ac.post("/api/v1/auth/register", json=payload)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_uk_user_sees_aadc_consent_at_registration(client):
    """A user registering from GB gets requires_aadc_consent=True."""
    ac, _ = client
    body = await _register(ac, "uk-1@example.com", country_code="GB")
    assert body["requires_aadc_consent"] is True


@pytest.mark.asyncio
async def test_non_uk_user_does_not_see_aadc_consent(client):
    """US/EU users do not get the AADC follow-up step."""
    ac, _ = client
    us_body = await _register(ac, "us-1@example.com", country_code="US")
    assert us_body["requires_aadc_consent"] is False

    no_country_body = await _register(ac, "no-country-1@example.com")
    assert no_country_body["requires_aadc_consent"] is False


@pytest.mark.asyncio
async def test_uk_user_can_record_aadc_consent(client):
    """POST /uk-aadc/consent records the consent and status reflects it."""
    ac, _ = client
    body = await _register(ac, "uk-2@example.com", country_code="GB")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    pre = await ac.get("/api/v1/compliance/uk-aadc/status", headers=headers)
    assert pre.status_code == 200
    assert pre.json()["consented"] is False
    assert pre.json()["current_consent_version"] == "uk_aadc_2026_v1"

    record = await ac.post(
        "/api/v1/compliance/uk-aadc/consent",
        json={
            "consent_version": "uk_aadc_2026_v1",
            "accepted": True,
        },
        headers=headers,
    )
    assert record.status_code == 201, record.text
    assert record.json()["consent_version"] == "uk_aadc_2026_v1"

    post = await ac.get("/api/v1/compliance/uk-aadc/status", headers=headers)
    assert post.json()["consented"] is True


@pytest.mark.asyncio
async def test_uk_aadc_refusal_rejected(client):
    """accepted=False returns 422 (UK AADC consent is mandatory for service use)."""
    ac, _ = client
    body = await _register(ac, "uk-3@example.com", country_code="GB")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    resp = await ac.post(
        "/api/v1/compliance/uk-aadc/consent",
        json={"consent_version": "uk_aadc_2026_v1", "accepted": False},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_uk_aadc_stale_version_rejected(client):
    """Old consent versions return 422 — user must re-accept current version."""
    ac, _ = client
    body = await _register(ac, "uk-4@example.com", country_code="GB")
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    resp = await ac.post(
        "/api/v1/compliance/uk-aadc/consent",
        json={"consent_version": "uk_aadc_2024_v0", "accepted": True},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_geolocation_default_off_for_uk_under_18():
    """Privacy defaults already enforce geolocation OFF for all child age tiers."""
    for tier in ("young", "preteen", "teen"):
        defaults = get_default_privacy_settings(tier)
        assert defaults["settings"]["geolocation_enabled"] is False, (
            f"AADC requires geolocation OFF by default for {tier}"
        )


@pytest.mark.asyncio
async def test_aadc_no_nudge_techniques_for_under_18():
    """Privacy defaults disable third-party data sharing for child age tiers
    (AADC Standard 13 — no nudge techniques to weaken privacy)."""
    for tier in ("young", "preteen", "teen"):
        defaults = get_default_privacy_settings(tier)
        assert defaults["settings"]["third_party_sharing_enabled"] is False
        assert defaults["settings"]["data_sharing_enabled"] is False
