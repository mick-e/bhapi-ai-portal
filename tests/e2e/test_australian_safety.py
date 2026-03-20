"""End-to-end tests for Australian eSafety Commissioner compliance endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

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
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_user(e2e_session):
    user = User(
        id=uuid.uuid4(),
        email=f"esafety-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="eSafety Admin",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def authed_e2e_client(e2e_engine, e2e_session, e2e_user):
    """Authenticated client with moderator role."""
    app = create_app()

    # Reset pipeline state for clean tests
    from src.moderation.esafety import pipeline as esafety
    esafety.reset()

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
            group_id=uuid.uuid4(),
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

    esafety.reset()


# ---------------------------------------------------------------------------
# Complaint submission E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_complaint_e2e(authed_e2e_client):
    """Submit a complaint via API and get response."""
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-content-001",
        "category": "cyberbullying",
        "evidence": "Bullying messages in chat",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == "local-e2e-content-001"
    assert body["status"] == "pending"
    assert "deadline" in body


@pytest.mark.asyncio
async def test_submit_complaint_missing_content_id(authed_e2e_client):
    """Missing content_id returns 422."""
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "category": "cyberbullying",
        "evidence": "Evidence text",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_complaint_missing_category(authed_e2e_client):
    """Missing category returns 422."""
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-content-002",
        "evidence": "Evidence text",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_complaint_invalid_category(authed_e2e_client):
    """Invalid category value returns error."""
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-content-003",
        "category": "not_a_real_category",
        "evidence": "Evidence text",
    })
    # StrEnum will raise ValueError -> 500 or 422
    assert resp.status_code in (422, 500)


# ---------------------------------------------------------------------------
# Takedown E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_takedown_e2e(authed_e2e_client):
    """Submit complaint then mark as taken down."""
    # First submit
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-td-001",
        "category": "image_based_abuse",
        "evidence": "Abusive image",
    })

    # Then take down
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/e2e-td-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "taken_down"
    assert body["content_id"] == "e2e-td-001"


@pytest.mark.asyncio
async def test_mark_takedown_not_found(authed_e2e_client):
    """Takedown of nonexistent content returns 404."""
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_e2e(authed_e2e_client):
    """Get takedown status via API."""
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-status-001",
        "category": "cyberbullying",
        "evidence": "Evidence",
    })

    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/status/e2e-status-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_id"] == "e2e-status-001"
    assert body["is_overdue"] is False
    assert body["taken_down"] is False
    assert body["time_remaining_seconds"] > 0


@pytest.mark.asyncio
async def test_get_status_not_found(authed_e2e_client):
    """Status of nonexistent content returns 404."""
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/status/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_after_takedown(authed_e2e_client):
    """Status shows taken_down after marking."""
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "e2e-status-002",
        "category": "online_content",
        "evidence": "Evidence",
    })
    await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/e2e-status-002")

    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/status/e2e-status-002")
    assert resp.status_code == 200
    body = resp.json()
    assert body["taken_down"] is True
    assert body["taken_down_at"] is not None


# ---------------------------------------------------------------------------
# Dashboard E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_empty(authed_e2e_client):
    """Dashboard with no complaints."""
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_complaints"] == 0
    assert body["sla_compliance_rate"] == 100.0


@pytest.mark.asyncio
async def test_dashboard_with_complaints(authed_e2e_client):
    """Dashboard reflects submitted complaints."""
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "dash-001",
        "category": "cyberbullying",
        "evidence": "Evidence 1",
    })
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "dash-002",
        "category": "image_based_abuse",
        "evidence": "Evidence 2",
    })
    await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/dash-001")

    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_complaints"] == 2
    assert body["taken_down"] == 1
    assert body["pending"] == 1


# ---------------------------------------------------------------------------
# Overdue E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overdue_empty(authed_e2e_client):
    """Overdue endpoint returns empty when nothing is overdue."""
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/overdue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_submit_multiple_categories(authed_e2e_client):
    """Submit complaints across all category types."""
    for cat in ["cyberbullying", "image_based_abuse", "illegal_harmful_content", "online_content"]:
        resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
            "content_id": f"multi-{cat}",
            "category": cat,
            "evidence": f"Evidence for {cat}",
        })
        assert resp.status_code == 200
    dash = await authed_e2e_client.get("/api/v1/moderation/esafety/dashboard")
    assert dash.json()["total_complaints"] == 4


@pytest.mark.asyncio
async def test_double_takedown_same_content(authed_e2e_client):
    """Taking down same content twice succeeds (idempotent)."""
    await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "double-td",
        "category": "cyberbullying",
        "evidence": "Evidence",
    })
    resp1 = await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/double-td")
    assert resp1.status_code == 200
    resp2 = await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/double-td")
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_full_complaint_lifecycle(authed_e2e_client):
    """Full lifecycle: submit -> check status -> takedown -> verify."""
    # Submit
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "lifecycle-001",
        "category": "illegal_harmful_content",
        "evidence": "Harmful content detected",
    })
    assert resp.status_code == 200

    # Check status (pending)
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/status/lifecycle-001")
    assert resp.status_code == 200
    assert resp.json()["taken_down"] is False

    # Dashboard shows 1 pending
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.json()["pending"] >= 1

    # Take down
    resp = await authed_e2e_client.post("/api/v1/moderation/esafety/takedown/lifecycle-001")
    assert resp.status_code == 200

    # Verify taken down
    resp = await authed_e2e_client.get("/api/v1/moderation/esafety/status/lifecycle-001")
    assert resp.json()["taken_down"] is True
