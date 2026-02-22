"""E2E tests for the capture gateway module.

Covers event ingestion (extension/dns/api channels), listing with filters,
device registration, and validation rejection.
"""

import pytest
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="capture@test.com"):
    """Register a user, login, return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Capture Tester",
        "account_type": "family",
    })
    user_id = reg.json()["id"]
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    return login.json()["access_token"], user_id


async def _create_group_and_member(client, headers):
    """Create a group, add a child member, return (group_id, member_id)."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Capture Family",
        "type": "family",
    }, headers=headers)
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    member_id = mem.json()["id"]
    return group_id, member_id


def _event_payload(group_id, member_id, platform="chatgpt", event_type="prompt"):
    """Build a valid EventPayload dict."""
    return {
        "group_id": group_id,
        "member_id": member_id,
        "platform": platform,
        "session_id": "sess-001",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def capture_client():
    """Test client with committing DB session for capture tests."""
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
        yield client

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Extension channel tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capture_extension_event(capture_client):
    """POST /capture/events ingests an extension event (201)."""
    token, _ = await _register_and_login(capture_client)
    headers = {"Authorization": f"Bearer {token}"}
    group_id, member_id = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(group_id, member_id),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_channel"] == "extension"
    assert data["platform"] == "chatgpt"
    assert data["event_type"] == "prompt"
    assert data["risk_processed"] is False


@pytest.mark.asyncio
async def test_capture_extension_response_event(capture_client):
    """Ingest a response event type via extension channel."""
    token, _ = await _register_and_login(capture_client, "ext2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, event_type="response"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "response"


@pytest.mark.asyncio
async def test_capture_extension_session_start(capture_client):
    """Ingest session_start event."""
    token, _ = await _register_and_login(capture_client, "ext3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, event_type="session_start"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "session_start"


@pytest.mark.asyncio
async def test_capture_extension_session_end(capture_client):
    """Ingest session_end event."""
    token, _ = await _register_and_login(capture_client, "ext4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, event_type="session_end"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "session_end"


# ---------------------------------------------------------------------------
# DNS channel tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capture_dns_event(capture_client):
    """POST /capture/dns-events ingests a DNS event (201)."""
    token, _ = await _register_and_login(capture_client, "dns@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/dns-events",
        json=_event_payload(gid, mid, platform="gemini"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["source_channel"] == "dns"
    assert resp.json()["platform"] == "gemini"


# ---------------------------------------------------------------------------
# API channel tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capture_api_event(capture_client):
    """POST /capture/api-events ingests an API webhook event (201)."""
    token, _ = await _register_and_login(capture_client, "api@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/api-events",
        json=_event_payload(gid, mid, platform="claude"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["source_channel"] == "api"
    assert resp.json()["platform"] == "claude"


# ---------------------------------------------------------------------------
# All platforms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capture_copilot_platform(capture_client):
    """Ingest event for copilot platform."""
    token, _ = await _register_and_login(capture_client, "copilot@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, platform="copilot"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "copilot"


@pytest.mark.asyncio
async def test_capture_grok_platform(capture_client):
    """Ingest event for grok platform."""
    token, _ = await _register_and_login(capture_client, "grok@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, platform="grok"),
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["platform"] == "grok"


# ---------------------------------------------------------------------------
# List events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_events_empty(capture_client):
    """GET /capture/events returns empty list for new group."""
    token, _ = await _register_and_login(capture_client, "list0@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.get(
        f"/api/v1/capture/events?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_events_returns_ingested(capture_client):
    """List events after ingesting some."""
    token, _ = await _register_and_login(capture_client, "list1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    # Ingest 3 events
    for _ in range(3):
        await capture_client.post(
            "/api/v1/capture/events",
            json=_event_payload(gid, mid),
            headers=headers,
        )

    resp = await capture_client.get(
        f"/api/v1/capture/events?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_list_events_filter_by_member(capture_client):
    """Filter events by member_id."""
    token, _ = await _register_and_login(capture_client, "list2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    # Add second member
    mem2 = await capture_client.post(f"/api/v1/groups/{gid}/members", json={
        "display_name": "Child 2",
        "role": "member",
    }, headers=headers)
    mid2 = mem2.json()["id"]

    # Ingest events for each member
    await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid),
        headers=headers,
    )
    await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid2),
        headers=headers,
    )

    resp = await capture_client.get(
        f"/api/v1/capture/events?group_id={gid}&member_id={mid}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["member_id"] == mid


@pytest.mark.asyncio
async def test_list_events_filter_by_platform(capture_client):
    """Filter events by platform."""
    token, _ = await _register_and_login(capture_client, "list3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, platform="chatgpt"),
        headers=headers,
    )
    await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, platform="claude"),
        headers=headers,
    )

    resp = await capture_client.get(
        f"/api/v1/capture/events?group_id={gid}&platform=claude",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["platform"] == "claude"


@pytest.mark.asyncio
async def test_list_events_pagination(capture_client):
    """Pagination: limit and offset."""
    token, _ = await _register_and_login(capture_client, "list4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    for _ in range(5):
        await capture_client.post(
            "/api/v1/capture/events",
            json=_event_payload(gid, mid),
            headers=headers,
        )

    resp = await capture_client.get(
        f"/api/v1/capture/events?group_id={gid}&limit=2&offset=0",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Device registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_device(capture_client):
    """POST /capture/devices/register creates a device (201)."""
    token, _ = await _register_and_login(capture_client, "dev@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/devices/register",
        json={
            "group_id": gid,
            "member_id": mid,
            "device_name": "Chromebook #1",
            "setup_code": "ABC123",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["device_name"] == "Chromebook #1"
    assert data["setup_code"] == "ABC123"
    assert data["group_id"] == gid
    assert data["member_id"] == mid


@pytest.mark.asyncio
async def test_list_devices(capture_client):
    """GET /capture/devices lists registered devices."""
    token, _ = await _register_and_login(capture_client, "devlist@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    await capture_client.post(
        "/api/v1/capture/devices/register",
        json={
            "group_id": gid,
            "member_id": mid,
            "device_name": "iPad",
            "setup_code": "XYZ789",
        },
        headers=headers,
    )

    resp = await capture_client.get(
        f"/api/v1/capture/devices?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) >= 1
    assert devices[0]["device_name"] == "iPad"


@pytest.mark.asyncio
async def test_list_devices_empty(capture_client):
    """Empty device list for new group."""
    token, _ = await _register_and_login(capture_client, "devempty@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.get(
        f"/api/v1/capture/devices?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Validation: invalid platform
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_platform_rejected(capture_client):
    """Invalid platform returns 422."""
    token, _ = await _register_and_login(capture_client, "val1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, platform="unknown_platform"),
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Validation: invalid event_type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_event_type_rejected(capture_client):
    """Invalid event_type returns 422."""
    token, _ = await _register_and_login(capture_client, "val2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid, event_type="invalid_type"),
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Validation: missing fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_session_id_rejected(capture_client):
    """Missing session_id returns 422."""
    token, _ = await _register_and_login(capture_client, "val3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    payload = _event_payload(gid, mid)
    del payload["session_id"]

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_capture_event_has_id_and_timestamp(capture_client):
    """Response includes id and created_at."""
    token, _ = await _register_and_login(capture_client, "meta@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=_event_payload(gid, mid),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_capture_requires_auth(capture_client):
    """Capture endpoint requires authentication."""
    resp = await capture_client.post("/api/v1/capture/events", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_event_metadata_stored(capture_client):
    """Optional metadata field is preserved."""
    token, _ = await _register_and_login(capture_client, "metadata@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(capture_client, headers)

    payload = _event_payload(gid, mid)
    payload["metadata"] = {"browser": "chrome", "version": "120"}

    resp = await capture_client.post(
        "/api/v1/capture/events",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
