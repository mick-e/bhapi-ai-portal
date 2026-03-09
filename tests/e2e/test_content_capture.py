"""E2E tests for content-aware capture with encryption.

Covers content capture, deduplication, decryption retrieval,
auth enforcement, and 404 handling.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, email="content@example.com"):
    """Register a user, return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Content Tester",
        "account_type": "family",
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group_and_member(client, headers):
    """Create a group, add a child member, return (group_id, member_id)."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Content Family",
        "type": "family",
    }, headers=headers)
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    member_id = mem.json()["id"]
    return group_id, member_id


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def content_client():
    """Test client with committing DB session for content capture tests."""
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
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_content_success(content_client):
    """POST /capture/content ingests content with encryption (201)."""
    token, _ = await _register_and_login(content_client)
    headers = {"Authorization": f"Bearer {token}"}
    group_id, member_id = await _create_group_and_member(content_client, headers)

    resp = await content_client.post(
        "/api/v1/capture/content",
        json={
            "group_id": group_id,
            "member_id": member_id,
            "platform": "chatgpt",
            "content": "Tell me about dinosaurs",
            "content_type": "prompt",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == group_id
    assert data["member_id"] == member_id
    assert data["platform"] == "chatgpt"
    assert data["content_type"] == "prompt"
    assert data["enhanced_monitoring"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_capture_content_deduplication(content_client):
    """POST same content twice within 1 minute returns the same event (dedup)."""
    token, _ = await _register_and_login(content_client, "dedup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    group_id, member_id = await _create_group_and_member(content_client, headers)

    payload = {
        "group_id": group_id,
        "member_id": member_id,
        "platform": "chatgpt",
        "content": "What is the meaning of life?",
        "content_type": "prompt",
    }

    resp1 = await content_client.post(
        "/api/v1/capture/content", json=payload, headers=headers,
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    resp2 = await content_client.post(
        "/api/v1/capture/content", json=payload, headers=headers,
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    assert id1 == id2  # Same event returned due to deduplication


@pytest.mark.asyncio
async def test_retrieve_decrypted_content(content_client):
    """POST content, then GET it back decrypted — verify round-trip."""
    token, _ = await _register_and_login(content_client, "decrypt@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    group_id, member_id = await _create_group_and_member(content_client, headers)

    original_content = "Can you help me with my homework about volcanoes?"

    resp = await content_client.post(
        "/api/v1/capture/content",
        json={
            "group_id": group_id,
            "member_id": member_id,
            "platform": "gemini",
            "content": original_content,
            "content_type": "conversation",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    event_id = resp.json()["id"]

    # Retrieve decrypted content
    get_resp = await content_client.get(
        f"/api/v1/capture/content/{event_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["event_id"] == event_id
    assert data["content"] == original_content


@pytest.mark.asyncio
async def test_capture_content_without_auth(content_client):
    """POST /capture/content without auth returns 401."""
    resp = await content_client.post(
        "/api/v1/capture/content",
        json={
            "group_id": str(uuid4()),
            "member_id": str(uuid4()),
            "platform": "chatgpt",
            "content": "Hello",
            "content_type": "prompt",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retrieve_nonexistent_content(content_client):
    """GET /capture/content/{unknown_id} returns 404."""
    token, _ = await _register_and_login(content_client, "notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid4())
    resp = await content_client.get(
        f"/api/v1/capture/content/{fake_id}",
        headers=headers,
    )
    assert resp.status_code == 404
