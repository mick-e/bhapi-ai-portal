"""Security tests for the governance module.

Covers:
- Unauthenticated access (401)
- Input validation / injection
- Cross-school data isolation
- Authorization boundaries
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
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


@pytest.fixture
async def sec_session(sec_engine):
    async_session_maker = sessionmaker(
        sec_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def sec_data(sec_session):
    """Create two users with separate schools."""
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    school1_id = uuid.uuid4()
    school2_id = uuid.uuid4()

    for uid, email_prefix in [(user1_id, "sec1"), (user2_id, "sec2")]:
        user = User(
            id=uid,
            email=f"{email_prefix}-{uuid.uuid4().hex[:8]}@example.com",
            display_name=f"{email_prefix} user",
            account_type="school",
            email_verified=False,
            mfa_enabled=False,
        )
        sec_session.add(user)

    await sec_session.flush()

    for sid, uid, name in [
        (school1_id, user1_id, "School 1"),
        (school2_id, user2_id, "School 2"),
    ]:
        group = Group(
            id=sid, name=name, type="school", owner_id=uid, settings={},
        )
        sec_session.add(group)

    await sec_session.flush()

    return {
        "user1_id": user1_id,
        "user2_id": user2_id,
        "school1_id": school1_id,
        "school2_id": school2_id,
    }


@pytest.fixture
async def unauthed_client(sec_engine, sec_session):
    """Client without authentication."""
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


def _authed_client_for(sec_engine, sec_session, user_id, group_id=None):
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role="admin")

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def client1(sec_engine, sec_session, sec_data):
    async with _authed_client_for(
        sec_engine, sec_session, sec_data["user1_id"], sec_data["school1_id"],
    ) as c:
        yield c


@pytest_asyncio.fixture
async def client2(sec_engine, sec_session, sec_data):
    async with _authed_client_for(
        sec_engine, sec_session, sec_data["user2_id"], sec_data["school2_id"],
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


class TestUnauthenticatedAccess:
    """All governance endpoints should require authentication."""

    @pytest.mark.asyncio
    async def test_create_policy_no_auth(self, unauthed_client):
        resp = await unauthed_client.post("/api/v1/governance/policies", json={
            "school_id": str(uuid.uuid4()), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_policies_no_auth(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/v1/governance/policies", params={"school_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_policy_no_auth(self, unauthed_client):
        resp = await unauthed_client.get(f"/api/v1/governance/policies/{uuid.uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tools_no_auth(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/v1/governance/tools", params={"school_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_no_auth(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/v1/governance/dashboard", params={"school_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_template_no_auth(self, unauthed_client):
        resp = await unauthed_client.post("/api/v1/governance/templates/generate", json={
            "state_code": "OH", "policy_type": "ai_usage",
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    @pytest.mark.asyncio
    async def test_invalid_state_code_too_long(self, client1, sec_data):
        resp = await client1.post("/api/v1/governance/policies", json={
            "school_id": str(sec_data["school1_id"]),
            "state_code": "OHIO",
            "policy_type": "ai_usage",
            "content": {},
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_state_code_too_short(self, client1, sec_data):
        resp = await client1.post("/api/v1/governance/policies", json={
            "school_id": str(sec_data["school1_id"]),
            "state_code": "O",
            "policy_type": "ai_usage",
            "content": {},
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client1):
        resp = await client1.post("/api/v1/governance/policies", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_xss_in_content(self, client1, sec_data):
        """Content is stored as JSON, so XSS payloads are just strings."""
        resp = await client1.post("/api/v1/governance/policies", json={
            "school_id": str(sec_data["school1_id"]),
            "state_code": "OH",
            "policy_type": "ai_usage",
            "content": {"title": "<script>alert('xss')</script>"},
        })
        assert resp.status_code == 201
        # Stored as-is (JSON content, not rendered as HTML)
        assert "<script>" in resp.json()["content"]["title"]

    @pytest.mark.asyncio
    async def test_invalid_tool_risk_level(self, client1, sec_data):
        resp = await client1.post("/api/v1/governance/tools", json={
            "school_id": str(sec_data["school1_id"]),
            "tool_name": "T", "vendor": "V",
            "risk_level": "critical", "approval_status": "approved",
        })
        assert resp.status_code == 422
