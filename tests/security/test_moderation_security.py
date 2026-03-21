"""Security tests for the moderation module."""

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
async def sec_engine():
    """Create a security test engine."""
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
async def sec_session(sec_engine):
    """Create a security test session."""
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def sec_users(sec_session):
    """Create test users for security tests."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"secmod1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"secmod2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()
    return {"user1": user1, "user2": user2}


@pytest_asyncio.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def admin_client(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as admin."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_users["user1"].id,
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
async def member_client(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as member (non-moderator)."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_users["user2"].id,
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
# Auth enforcement tests (401 without token)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_queue_requires_auth(unauthed_client):
    """POST /queue without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_queue_requires_auth(unauthed_client):
    """GET /queue without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/queue")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_queue_entry_requires_auth(unauthed_client):
    """GET /queue/{id} without auth returns 401."""
    resp = await unauthed_client.get(f"/api/v1/moderation/queue/{uuid.uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_decide_requires_auth(unauthed_client):
    """PATCH /queue/{id}/decide without auth returns 401."""
    resp = await unauthed_client.patch(
        f"/api/v1/moderation/queue/{uuid.uuid4()}/decide",
        json={"action": "approve"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_takedown_requires_auth(unauthed_client):
    """POST /takedown without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/moderation/takedown", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "reason": "Bad content",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_requires_auth(unauthed_client):
    """GET /dashboard without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/dashboard")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_report_requires_auth(unauthed_client):
    """POST /reports without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "Spam",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_reports_requires_auth(unauthed_client):
    """GET /reports without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/reports")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Role-based access control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_cannot_decide(member_client, admin_client):
    """Members (non-moderator) cannot process queue decisions."""
    # Admin creates an entry
    create_resp = await admin_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    # Member tries to decide — should get 403
    resp = await member_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "approve"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_member_cannot_takedown(member_client):
    """Members cannot perform takedowns."""
    resp = await member_client.post("/api/v1/moderation/takedown", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "reason": "I want to take this down",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_decide(admin_client):
    """Admin can process queue decisions."""
    create_resp = await admin_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    queue_id = create_resp.json()["id"]

    resp = await admin_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "approve"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_takedown(admin_client):
    """Admin can perform takedowns."""
    resp = await admin_client.post("/api/v1/moderation/takedown", json={
        "content_type": "media",
        "content_id": str(uuid.uuid4()),
        "reason": "Policy violation",
    })
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Report isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_only_sees_own_reports(member_client, admin_client, sec_users):
    """Non-moderator only sees their own reports, not others'."""
    # Admin creates a report
    await admin_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "Admin report",
    })
    # Member creates a report
    await member_client.post("/api/v1/moderation/reports", json={
        "target_type": "comment",
        "target_id": str(uuid.uuid4()),
        "reason": "Member report",
    })

    # Member lists reports — should only see their own
    resp = await member_client.get("/api/v1/moderation/reports")
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["reporter_id"] == str(sec_users["user2"].id)


@pytest.mark.asyncio
async def test_admin_sees_all_reports(admin_client, member_client):
    """Admin (moderator) sees all reports."""
    # Member creates a report
    await member_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "inappropriate",
    })
    # Admin creates a report
    await admin_client.post("/api/v1/moderation/reports", json={
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "spam",
    })

    resp = await admin_client.get("/api/v1/moderation/reports")
    assert resp.status_code == 200
    body = resp.json()
    # Admin should see at least 2 reports (both their own and member's)
    assert body["total"] >= 2


@pytest.mark.asyncio
async def test_member_can_submit_to_queue(member_client):
    """Members can submit content for moderation (but not decide)."""
    resp = await member_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 201
