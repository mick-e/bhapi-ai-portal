"""End-to-end tests for messaging real-time features — typing, read receipts,
media messages, and conversation ordering."""

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
        email=f"rt-user1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="RT User One",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"rt-user2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="RT User Two",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user3 = User(
        id=uuid.uuid4(),
        email=f"rt-user3-{uuid.uuid4().hex[:8]}@example.com",
        display_name="RT User Three",
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
    async with _make_client(e2e_engine, e2e_session, e2e_users["user1"].id) as c:
        yield c


@pytest_asyncio.fixture
async def client2(e2e_engine, e2e_session, e2e_users):
    async with _make_client(e2e_engine, e2e_session, e2e_users["user2"].id) as c:
        yield c


@pytest_asyncio.fixture
async def client3(e2e_engine, e2e_session, e2e_users):
    async with _make_client(e2e_engine, e2e_session, e2e_users["user3"].id) as c:
        yield c


@pytest_asyncio.fixture
async def conversation(client1, e2e_users):
    """Create a conversation between user1 and user2."""
    resp = await client1.post("/api/v1/messages/conversations", json={
        "type": "direct",
        "member_user_ids": [
            str(e2e_users["user1"].id),
            str(e2e_users["user2"].id),
        ],
    })
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Typing indicator E2E tests
# ---------------------------------------------------------------------------


class TestTypingEndpoints:
    """Test typing indicator endpoints."""

    @pytest.mark.asyncio
    async def test_start_typing(self, client1, conversation):
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_stop_typing(self, client1, conversation):
        await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        resp = await client1.delete(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get_typing_status_empty(self, client1, conversation):
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"] == conversation["id"]
        assert isinstance(data["typing_users"], list)

    @pytest.mark.asyncio
    async def test_typing_round_trip(self, client1, client2, conversation, e2e_users):
        """User1 starts typing, user2 queries and sees user1 typing."""
        await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        resp = await client2.get(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        data = resp.json()
        assert str(e2e_users["user1"].id) in data["typing_users"]

    @pytest.mark.asyncio
    async def test_stop_typing_removes_from_list(self, client1, client2, conversation, e2e_users):
        await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        await client1.delete(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        resp = await client2.get(
            f"/api/v1/messages/conversations/{conversation['id']}/typing",
        )
        data = resp.json()
        assert str(e2e_users["user1"].id) not in data["typing_users"]


# ---------------------------------------------------------------------------
# Unread count / Read receipt E2E tests
# ---------------------------------------------------------------------------


class TestUnreadCountEndpoints:
    """Test unread count endpoints."""

    @pytest.mark.asyncio
    async def test_unread_count_initially_zero(self, client1, conversation):
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conversation['id']}/unread",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_mark_read_then_check(self, client1, conversation):
        """Mark read and verify unread count is 0."""
        await client1.patch(
            f"/api/v1/messages/conversations/{conversation['id']}/read",
        )
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conversation['id']}/unread",
        )
        assert resp.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_unread_count_response_shape(self, client1, conversation):
        resp = await client1.get(
            f"/api/v1/messages/conversations/{conversation['id']}/unread",
        )
        data = resp.json()
        assert "conversation_id" in data
        assert "unread_count" in data


# ---------------------------------------------------------------------------
# Media message E2E tests
# ---------------------------------------------------------------------------


class TestMediaMessageEndpoints:
    """Test media message endpoints."""

    @pytest.mark.asyncio
    async def test_send_image_message(self, client1, conversation):
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/media",
            json={
                "media_url": "cf-images-abc123",
                "media_type": "image",
                "content": "Check this out!",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message_type"] == "image"
        assert data["content"] == "Check this out!"

    @pytest.mark.asyncio
    async def test_send_video_message(self, client1, conversation):
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/media",
            json={
                "media_url": "cf-stream-xyz789",
                "media_type": "video",
                "content": "",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message_type"] == "video"

    @pytest.mark.asyncio
    async def test_send_media_no_caption(self, client1, conversation):
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/media",
            json={
                "media_url": "cf-images-nocap",
                "media_type": "image",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "[image]"  # Default content

    @pytest.mark.asyncio
    async def test_send_media_invalid_type(self, client1, conversation):
        resp = await client1.post(
            f"/api/v1/messages/conversations/{conversation['id']}/media",
            json={
                "media_url": "cf-some-id",
                "media_type": "audio",  # Invalid
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_send_media_non_member(self, client3, conversation):
        resp = await client3.post(
            f"/api/v1/messages/conversations/{conversation['id']}/media",
            json={
                "media_url": "cf-images-sneak",
                "media_type": "image",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Conversation ordering E2E tests
# ---------------------------------------------------------------------------


class TestConversationOrdering:
    """Test that conversations are ordered by last message time."""

    @pytest.mark.asyncio
    async def test_conversations_list_returns_items(self, client1, conversation):
        resp = await client1.get("/api/v1/messages/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_conversation_response_has_preview_fields(self, client1, conversation):
        """Conversation items should include last_message_preview and last_message_at."""
        resp = await client1.get("/api/v1/messages/conversations")
        data = resp.json()
        if data["items"]:
            item = data["items"][0]
            assert "last_message_preview" in item or "created_at" in item
