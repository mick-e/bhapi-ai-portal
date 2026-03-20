"""End-to-end tests for the messaging module — HTTP endpoint tests."""

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
from src.main import create_app
from src.messaging.models import Message
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    """Create an E2E test engine."""
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
    """Create an E2E test session."""
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_users(e2e_session):
    """Create test users."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"user1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="User One",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"user2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="User Two",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user3 = User(
        id=uuid.uuid4(),
        email=f"user3-{uuid.uuid4().hex[:8]}@example.com",
        display_name="User Three",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add_all([user1, user2, user3])
    await e2e_session.flush()
    return {"user1": user1, "user2": user2, "user3": user3}


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
    """Create an authenticated test client for a specific user."""
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
            user_id=user_id,
            group_id=group_id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def client1(e2e_engine, e2e_session, e2e_users):
    """Authenticated client as user1."""
    async with _make_client(e2e_engine, e2e_session, e2e_users["user1"].id) as c:
        yield c


@pytest_asyncio.fixture
async def client2(e2e_engine, e2e_session, e2e_users):
    """Authenticated client as user2."""
    async with _make_client(e2e_engine, e2e_session, e2e_users["user2"].id) as c:
        yield c


@pytest_asyncio.fixture
async def client3(e2e_engine, e2e_session, e2e_users):
    """Authenticated client as user3 (non-member)."""
    async with _make_client(e2e_engine, e2e_session, e2e_users["user3"].id) as c:
        yield c


# ---------------------------------------------------------------------------
# Conversation E2E tests
# ---------------------------------------------------------------------------


class TestConversationEndpoints:
    """Test conversation CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_direct_conversation(self, client1, e2e_users):
        resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "direct"
        assert data["member_count"] == 2

    @pytest.mark.asyncio
    async def test_create_group_conversation(self, client1, e2e_users):
        resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "group",
            "title": "Test Group Chat",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
                str(e2e_users["user3"].id),
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "group"
        assert data["title"] == "Test Group Chat"
        assert data["member_count"] == 3

    @pytest.mark.asyncio
    async def test_create_direct_too_many_members(self, client1, e2e_users):
        resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
                str(e2e_users["user3"].id),
            ],
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self, client1):
        resp = await client1.get("/api/v1/messages/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_conversations(self, client1, e2e_users):
        await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        resp = await client1.get("/api/v1/messages/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_conversation(self, client1, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client1.get(f"/api/v1/messages/conversations/{conv_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == conv_id

    @pytest.mark.asyncio
    async def test_get_conversation_non_member(self, client1, client3, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client3.get(f"/api/v1/messages/conversations/{conv_id}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Message E2E tests
# ---------------------------------------------------------------------------


class TestMessageEndpoints:
    """Test message send/list endpoints."""

    @pytest.mark.asyncio
    async def test_send_message(self, client1, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conv_id}/messages",
            json={"content": "Hello!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello!"
        assert data["moderation_status"] == "pending"

    @pytest.mark.asyncio
    async def test_send_message_non_member(self, client1, client3, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client3.post(
            f"/api/v1/messages/conversations/{conv_id}/messages",
            json={"content": "Sneaky!"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_messages_empty(self, client1, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conv_id}/messages",
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_messages_pagination(self, client1, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conv_id}/messages?page=1&page_size=5",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    @pytest.mark.asyncio
    async def test_list_messages_non_member(self, client1, client3, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client3.get(
            f"/api/v1/messages/conversations/{conv_id}/messages",
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Mark read E2E tests
# ---------------------------------------------------------------------------


class TestMarkReadEndpoints:
    """Test mark-read endpoint."""

    @pytest.mark.asyncio
    async def test_mark_read(self, client1, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client1.patch(
            f"/api/v1/messages/conversations/{conv_id}/read",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_mark_read_non_member(self, client1, client3, e2e_users):
        create_resp = await client1.post("/api/v1/messages/conversations", json={
            "type": "direct",
            "member_user_ids": [
                str(e2e_users["user1"].id),
                str(e2e_users["user2"].id),
            ],
        })
        conv_id = create_resp.json()["id"]
        resp = await client3.patch(
            f"/api/v1/messages/conversations/{conv_id}/read",
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_conversation_pagination_params(self, client1):
        resp = await client1.get(
            "/api/v1/messages/conversations?page=2&page_size=5",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["page_size"] == 5
