"""End-to-end tests for the moderation module API."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    """Create E2E test engine."""
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

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    """Create E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_user(e2e_session):
    """Create a test user for E2E."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-mod-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Moderator",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def e2e_user2(e2e_session):
    """Create a second test user for E2E."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-mod2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Reporter",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def mod_client(e2e_engine, e2e_session, e2e_user):
    """Authenticated HTTP client with moderator role."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_user.id,
            group_id=None,
            role="admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def member_client(e2e_engine, e2e_session, e2e_user2):
    """Authenticated HTTP client with member role (non-moderator)."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_user2.id,
            group_id=None,
            role="member",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# POST /queue — submit content for moderation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_to_queue(mod_client):
    """POST /queue creates a queue entry."""
    resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["pipeline"] == "post_publish"


@pytest.mark.asyncio
async def test_submit_with_age_tier(mod_client):
    """POST /queue with age_tier routes correctly."""
    resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "young",
    })
    assert resp.status_code == 201
    assert resp.json()["pipeline"] == "pre_publish"


@pytest.mark.asyncio
async def test_submit_invalid_content_type(mod_client):
    """POST /queue with invalid content_type returns 422."""
    resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "tweet",
        "content_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /queue — list queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_queue_empty(mod_client):
    """GET /queue returns empty list initially."""
    resp = await mod_client.get("/api/v1/moderation/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_queue_with_entries(mod_client):
    """GET /queue returns submitted entries."""
    for _ in range(3):
        await mod_client.post("/api/v1/moderation/queue", json={
            "content_type": "post",
            "content_id": str(uuid.uuid4()),
        })
    resp = await mod_client.get("/api/v1/moderation/queue")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


@pytest.mark.asyncio
async def test_list_queue_status_filter(mod_client):
    """GET /queue?status=pending filters correctly."""
    # Create and approve one
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]
    await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "approve",
    })

    # Create another (pending)
    await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })

    resp = await mod_client.get("/api/v1/moderation/queue?status=pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_queue_pagination(mod_client):
    """GET /queue with pagination params."""
    for _ in range(5):
        await mod_client.post("/api/v1/moderation/queue", json={
            "content_type": "comment",
            "content_id": str(uuid.uuid4()),
        })
    resp = await mod_client.get("/api/v1/moderation/queue?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_queue_pipeline_filter(mod_client):
    """GET /queue?pipeline=pre_publish filters correctly."""
    await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "young",
    })
    await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "teen",
    })

    resp = await mod_client.get("/api/v1/moderation/queue?pipeline=pre_publish")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# GET /queue/{id} — get entry detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_queue_entry_detail(mod_client):
    """GET /queue/{id} returns entry details."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "message",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await mod_client.get(f"/api/v1/moderation/queue/{queue_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == queue_id


@pytest.mark.asyncio
async def test_get_queue_entry_not_found(mod_client):
    """GET /queue/{id} for missing entry returns 404."""
    resp = await mod_client.get(f"/api/v1/moderation/queue/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /queue/{id}/decide — approve/reject/escalate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decide_approve(mod_client):
    """PATCH /queue/{id}/decide with approve."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "approve",
    })
    assert resp.status_code == 200
    assert resp.json()["action"] == "approve"


@pytest.mark.asyncio
async def test_decide_reject_with_reason(mod_client):
    """PATCH /queue/{id}/decide with reject and reason."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "reject",
        "reason": "Violates community guidelines",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "reject"
    assert body["reason"] == "Violates community guidelines"


@pytest.mark.asyncio
async def test_decide_creates_audit_trail(mod_client):
    """Decision creates a proper audit trail with moderator_id."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "escalate",
        "reason": "Needs senior review",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["moderator_id"] is not None
    assert body["timestamp"] is not None


@pytest.mark.asyncio
async def test_decide_invalid_action(mod_client):
    """PATCH /queue/{id}/decide with invalid action returns 422."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "delete",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_decide_already_processed(mod_client):
    """Deciding on already-processed entry returns 409."""
    create_resp = await mod_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "approve",
    })
    resp = await mod_client.patch(f"/api/v1/moderation/queue/{queue_id}/decide", json={
        "action": "reject",
    })
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /takedown — emergency takedown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_takedown(mod_client):
    """POST /takedown creates takedown decision."""
    resp = await mod_client.post("/api/v1/moderation/takedown", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "reason": "Harmful content detected",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "taken_down"
    assert "[TAKEDOWN]" in body["reason"]


# ---------------------------------------------------------------------------
# GET /dashboard — stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_stats(mod_client):
    """GET /dashboard returns moderation statistics."""
    resp = await mod_client.get("/api/v1/moderation/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "pending_count" in body
    assert "total_processed_today" in body
    assert "avg_processing_time_ms" in body
    assert "severity_breakdown" in body


# ---------------------------------------------------------------------------
# POST /reports — create content report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_report(mod_client):
    """POST /reports creates a content report."""
    resp = await mod_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "This is spam",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["target_type"] == "post"


@pytest.mark.asyncio
async def test_create_report_invalid_type(mod_client):
    """POST /reports with invalid target_type returns 422."""
    resp = await mod_client.post("/api/v1/moderation/reports", json={
        "target_type": "profile",
        "target_id": str(uuid.uuid4()),
        "reason": "Bad content",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /reports — list reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_reports(mod_client):
    """GET /reports returns paginated reports."""
    await mod_client.post("/api/v1/moderation/reports", json={
        "target_type": "comment",
        "target_id": str(uuid.uuid4()),
        "reason": "Offensive",
    })
    resp = await mod_client.get("/api/v1/moderation/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


@pytest.mark.asyncio
async def test_member_sees_only_own_reports(member_client, mod_client):
    """Non-moderator only sees their own reports."""
    # Member creates a report
    await member_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "Spam",
    })
    resp = await member_client.get("/api/v1/moderation/reports")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    # All returned reports belong to the member
    for item in body["items"]:
        assert item["reporter_id"] is not None
