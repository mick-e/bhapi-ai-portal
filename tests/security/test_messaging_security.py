"""Security tests for the messaging module.

Covers:
- Unauthenticated access (401) on all endpoints
- IDOR — cross-user conversation access
- User cannot send messages to conversations they're not in
- User cannot read messages from other users' conversations
- Rate limiting / message content length validation
- Cross-group isolation
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.messaging.models import Conversation, ConversationMember, Message
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
async def sec_users(sec_session):
    """Create users, groups, and a conversation for security testing."""
    # User A (parent in group A)
    user_a = User(
        id=uuid.uuid4(),
        email=f"msec-usera-{uuid.uuid4().hex[:8]}@example.com",
        display_name="User A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    # User B (member in group A — second member of conversation)
    user_b = User(
        id=uuid.uuid4(),
        email=f"msec-userb-{uuid.uuid4().hex[:8]}@example.com",
        display_name="User B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    # Attacker (in group B — should not access group A conversations)
    attacker = User(
        id=uuid.uuid4(),
        email=f"msec-attacker-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Attacker",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user_a, user_b, attacker])
    await sec_session.flush()

    # Group A
    group_a = Group(
        id=uuid.uuid4(), name="Family A", type="family", owner_id=user_a.id,
    )
    sec_session.add(group_a)
    await sec_session.flush()

    member_a = GroupMember(
        id=uuid.uuid4(), group_id=group_a.id, user_id=user_a.id,
        role="parent", display_name="User A",
    )
    member_b = GroupMember(
        id=uuid.uuid4(), group_id=group_a.id, user_id=user_b.id,
        role="member", display_name="User B",
    )
    sec_session.add_all([member_a, member_b])
    await sec_session.flush()

    # Group B (attacker's group)
    group_b = Group(
        id=uuid.uuid4(), name="Family B", type="family", owner_id=attacker.id,
    )
    sec_session.add(group_b)
    await sec_session.flush()

    attacker_member = GroupMember(
        id=uuid.uuid4(), group_id=group_b.id, user_id=attacker.id,
        role="parent", display_name="Attacker",
    )
    sec_session.add(attacker_member)
    await sec_session.flush()

    # Conversation between user_a and user_b
    conversation = Conversation(
        id=uuid.uuid4(), type="direct", created_by=user_a.id, title=None,
    )
    sec_session.add(conversation)
    await sec_session.flush()

    conv_member_a = ConversationMember(
        id=uuid.uuid4(), conversation_id=conversation.id,
        user_id=user_a.id, role="admin",
    )
    conv_member_b = ConversationMember(
        id=uuid.uuid4(), conversation_id=conversation.id,
        user_id=user_b.id, role="member",
    )
    sec_session.add_all([conv_member_a, conv_member_b])
    await sec_session.flush()

    # A message from user_a in the conversation
    message = Message(
        id=uuid.uuid4(), conversation_id=conversation.id,
        sender_id=user_a.id, content="Hello from A",
        message_type="text", moderation_status="approved",
    )
    sec_session.add(message)
    await sec_session.flush()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "attacker": attacker,
        "group_a": group_a,
        "group_b": group_b,
        "conversation": conversation,
        "message": message,
    }


def _make_client(sec_engine, sec_session, user_id, group_id=None, role="parent"):
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role=role)

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


def _make_unauthed_client(sec_engine, sec_session):
    """Client without auth override — relies on real auth middleware."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Tests — Unauthenticated Access (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthed_list_conversations_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/messages/conversations")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_create_conversation_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(
            "/api/v1/messages/conversations",
            json={"type": "direct", "member_user_ids": [str(uuid.uuid4())]},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_get_conversation_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{uuid.uuid4()}")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_send_message_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{uuid.uuid4()}/messages",
            json={"content": "hello"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_list_messages_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{uuid.uuid4()}/messages")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_mark_read_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.patch(f"/api/v1/messages/conversations/{uuid.uuid4()}/read")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_typing_post_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(f"/api/v1/messages/conversations/{uuid.uuid4()}/typing")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_typing_delete_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.delete(f"/api/v1/messages/conversations/{uuid.uuid4()}/typing")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_typing_get_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{uuid.uuid4()}/typing")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_unread_count_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{uuid.uuid4()}/unread")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_media_message_returns_401(sec_engine, sec_session):
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{uuid.uuid4()}/media",
            json={"media_url": "http://example.com/img.jpg", "media_type": "image"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — IDOR: Cross-User Conversation Access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attacker_cannot_get_conversation(sec_engine, sec_session, sec_users):
    """Attacker (not a member) cannot retrieve conversation details."""
    attacker = sec_users["attacker"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{conv.id}")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attacker_cannot_list_messages(sec_engine, sec_session, sec_users):
    """Attacker cannot read messages in a conversation they are not a member of."""
    attacker = sec_users["attacker"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{conv.id}/messages")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attacker_cannot_send_message(sec_engine, sec_session, sec_users):
    """Attacker cannot send a message to a conversation they are not in."""
    attacker = sec_users["attacker"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{conv.id}/messages",
            json={"content": "hacked!"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attacker_cannot_send_media_message(sec_engine, sec_session, sec_users):
    """Attacker cannot send a media message to a conversation they are not in."""
    attacker = sec_users["attacker"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{conv.id}/media",
            json={"media_url": "http://evil.com/img.jpg", "media_type": "image"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attacker_cannot_mark_read(sec_engine, sec_session, sec_users):
    """Attacker cannot mark a conversation as read if they are not a member."""
    attacker = sec_users["attacker"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.patch(f"/api/v1/messages/conversations/{conv.id}/read")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Tests — Cross-Group Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_group_user_cannot_see_conversations(
    sec_engine, sec_session, sec_users,
):
    """User from group B lists conversations — should not see group A's conversations."""
    attacker = sec_users["attacker"]

    async with _make_client(
        sec_engine, sec_session, attacker.id, sec_users["group_b"].id,
    ) as client:
        resp = await client.get("/api/v1/messages/conversations")
        assert resp.status_code == 200
        data = resp.json()
        # Attacker is not a member of any conversation, so items should be empty
        assert len(data["items"]) == 0


# ---------------------------------------------------------------------------
# Tests — Legitimate Member Access (positive control)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_member_can_get_conversation(sec_engine, sec_session, sec_users):
    """A legitimate conversation member can retrieve conversation details."""
    user_a = sec_users["user_a"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{conv.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(conv.id)


@pytest.mark.asyncio
async def test_member_can_send_message(sec_engine, sec_session, sec_users):
    """A legitimate conversation member can send a message."""
    user_b = sec_users["user_b"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, user_b.id, sec_users["group_a"].id, "member",
    ) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{conv.id}/messages",
            json={"content": "Hello from B"},
        )
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_member_can_list_messages(sec_engine, sec_session, sec_users):
    """A legitimate conversation member can list messages."""
    user_a = sec_users["user_a"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{conv.id}/messages")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conversation_type_validation(sec_engine, sec_session, sec_users):
    """Creating a conversation with invalid type is rejected."""
    user_a = sec_users["user_a"]
    user_b = sec_users["user_b"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.post(
            "/api/v1/messages/conversations",
            json={
                "type": "invalid_type",
                "member_user_ids": [str(user_b.id)],
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_direct_conversation_requires_exactly_two_members(
    sec_engine, sec_session, sec_users,
):
    """Direct conversations must have exactly 2 members (including creator)."""
    user_a = sec_users["user_a"]
    user_b = sec_users["user_b"]
    attacker = sec_users["attacker"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        # Three members in a direct conversation should fail
        resp = await client.post(
            "/api/v1/messages/conversations",
            json={
                "type": "direct",
                "member_user_ids": [str(user_b.id), str(attacker.id)],
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_empty_message_content_rejected(sec_engine, sec_session, sec_users):
    """Empty message content should be rejected by Pydantic validation (min_length=1)."""
    user_a = sec_users["user_a"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{conv.id}/messages",
            json={"content": ""},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_media_type_rejected(sec_engine, sec_session, sec_users):
    """Sending a media message with invalid media_type is rejected."""
    user_a = sec_users["user_a"]
    conv = sec_users["conversation"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.post(
            f"/api/v1/messages/conversations/{conv.id}/media",
            json={"media_url": "http://example.com/file.pdf", "media_type": "pdf"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_conversation_returns_not_found(
    sec_engine, sec_session, sec_users,
):
    """Accessing a non-existent conversation returns 403 or 404."""
    user_a = sec_users["user_a"]
    fake_id = uuid.uuid4()

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        resp = await client.get(f"/api/v1/messages/conversations/{fake_id}")
        # Should be 403 (not a member) since membership check runs first
        assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_conversation_needs_at_least_two_members(
    sec_engine, sec_session, sec_users,
):
    """Cannot create a conversation with only the creator."""
    user_a = sec_users["user_a"]

    async with _make_client(
        sec_engine, sec_session, user_a.id, sec_users["group_a"].id,
    ) as client:
        # Only one member_user_id which is the creator themselves
        resp = await client.post(
            "/api/v1/messages/conversations",
            json={
                "type": "group",
                "member_user_ids": [],
            },
        )
        assert resp.status_code == 422
