"""Security tests for Australian eSafety Commissioner compliance endpoints."""

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
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401."""
    app = create_app()

    # Reset pipeline
    from src.moderation.esafety import pipeline as esafety
    esafety.reset()

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

    esafety.reset()


@pytest_asyncio.fixture
async def member_client(sec_engine, sec_session):
    """HTTP client authenticated as a regular member (not moderator)."""
    app = create_app()

    from src.moderation.esafety import pipeline as esafety
    esafety.reset()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_member_auth():
        return GroupContext(
            user_id=uuid.uuid4(),
            group_id=uuid.uuid4(),
            role="member",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_member_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client

    esafety.reset()


@pytest_asyncio.fixture
async def admin_client(sec_engine, sec_session):
    """HTTP client authenticated as admin."""
    app = create_app()

    from src.moderation.esafety import pipeline as esafety
    esafety.reset()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_admin_auth():
        return GroupContext(
            user_id=uuid.uuid4(),
            group_id=uuid.uuid4(),
            role="admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_admin_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client

    esafety.reset()


# ---------------------------------------------------------------------------
# Auth enforcement (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_complaint_requires_auth(unauthed_client):
    """POST /esafety/complaints without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "sec-001",
        "category": "cyberbullying",
        "evidence": "Test",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_takedown_requires_auth(unauthed_client):
    """POST /esafety/takedown/{id} without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/moderation/esafety/takedown/sec-001")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_status_requires_auth(unauthed_client):
    """GET /esafety/status/{id} without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/esafety/status/sec-001")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_requires_auth(unauthed_client):
    """GET /esafety/dashboard without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_overdue_requires_auth(unauthed_client):
    """GET /esafety/overdue without auth returns 401."""
    resp = await unauthed_client.get("/api/v1/moderation/esafety/overdue")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Role enforcement (403 for non-moderators)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_complaint_requires_moderator(member_client):
    """POST /esafety/complaints as member returns 403."""
    resp = await member_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "sec-002",
        "category": "cyberbullying",
        "evidence": "Test",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_takedown_requires_moderator(member_client):
    """POST /esafety/takedown as member returns 403."""
    resp = await member_client.post("/api/v1/moderation/esafety/takedown/sec-002")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_overdue_requires_moderator(member_client):
    """GET /esafety/overdue as member returns 403."""
    resp = await member_client.get("/api/v1/moderation/esafety/overdue")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin access works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_submit_complaint(admin_client):
    """Admin role can submit complaints."""
    resp = await admin_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "sec-admin-001",
        "category": "cyberbullying",
        "evidence": "Evidence text",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_view_dashboard(admin_client):
    """Admin role can view dashboard."""
    resp = await admin_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_member_can_view_dashboard(member_client):
    """Members CAN view dashboard (read-only, no moderator check)."""
    resp = await member_client.get("/api/v1/moderation/esafety/dashboard")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_member_can_view_status(member_client, admin_client):
    """Members CAN view status (read-only endpoint)."""
    # Admin creates a complaint first
    await admin_client.post("/api/v1/moderation/esafety/complaints", json={
        "content_id": "sec-view-001",
        "category": "cyberbullying",
        "evidence": "Evidence",
    })
    # Member can read status (but the pipeline is per-process, so need same app)
    # Since fixtures use different app instances, just verify the endpoint auth
    resp = await member_client.get("/api/v1/moderation/esafety/status/sec-view-001")
    # Will be 404 (different pipeline instance) but NOT 401 or 403
    assert resp.status_code in (200, 404)
