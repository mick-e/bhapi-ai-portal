"""Unit tests for the ReadReceiptManager — unread counts, read status."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.messaging.models import Conversation, ConversationMember, Message
from src.realtime.receipts import ReadReceiptManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def users(test_session: AsyncSession):
    """Create two test users."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"receipt1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Receipts User1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"receipt2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Receipts User2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add_all([user1, user2])
    await test_session.flush()
    return {"user1": user1, "user2": user2}


@pytest_asyncio.fixture
async def conversation(test_session: AsyncSession, users):
    """Create a conversation with two members."""
    conv = Conversation(
        id=uuid.uuid4(),
        type="direct",
        created_by=users["user1"].id,
    )
    test_session.add(conv)
    await test_session.flush()

    m1 = ConversationMember(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        user_id=users["user1"].id,
        role="admin",
    )
    m2 = ConversationMember(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        user_id=users["user2"].id,
        role="member",
    )
    test_session.add_all([m1, m2])
    await test_session.flush()
    return conv


@pytest_asyncio.fixture
async def messages(test_session: AsyncSession, users, conversation):
    """Create some approved messages in the conversation."""
    msgs = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)
    for i in range(5):
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            sender_id=users["user2"].id,  # sent by user2
            content=f"Message {i}",
            message_type="text",
            moderation_status="approved",
        )
        test_session.add(msg)
        msgs.append(msg)
    await test_session.flush()
    return msgs


# ---------------------------------------------------------------------------
# mark_read
# ---------------------------------------------------------------------------


class TestMarkRead:
    """Test marking conversations as read."""

    @pytest.mark.asyncio
    async def test_mark_read_updates_timestamp(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        ts = await mgr.mark_read(
            test_session, conversation.id, users["user1"].id,
        )
        assert isinstance(ts, datetime)
        assert ts.tzinfo is not None

    @pytest.mark.asyncio
    async def test_mark_read_with_explicit_timestamp(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        explicit_ts = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
        ts = await mgr.mark_read(
            test_session, conversation.id, users["user1"].id,
            read_at=explicit_ts,
        )
        assert ts == explicit_ts

    @pytest.mark.asyncio
    async def test_mark_read_no_membership(self, test_session, conversation):
        """mark_read with unknown user returns timestamp without error."""
        mgr = ReadReceiptManager()
        unknown_id = uuid.uuid4()
        ts = await mgr.mark_read(
            test_session, conversation.id, unknown_id,
        )
        assert isinstance(ts, datetime)

    @pytest.mark.asyncio
    async def test_mark_read_updates_member_record(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        await mgr.mark_read(
            test_session, conversation.id, users["user1"].id,
        )
        last_read = await mgr.get_last_read(
            test_session, conversation.id, users["user1"].id,
        )
        assert last_read is not None


# ---------------------------------------------------------------------------
# get_unread_count
# ---------------------------------------------------------------------------


class TestGetUnreadCount:
    """Test unread message counting."""

    @pytest.mark.asyncio
    async def test_unread_count_all_unread(
        self, test_session, users, conversation, messages,
    ):
        """All messages from user2 are unread for user1."""
        mgr = ReadReceiptManager()
        count = await mgr.get_unread_count(
            test_session, conversation.id, users["user1"].id,
        )
        assert count == 5

    @pytest.mark.asyncio
    async def test_unread_count_after_mark_read(
        self, test_session, users, conversation, messages,
    ):
        """After marking read, unread count should be 0."""
        mgr = ReadReceiptManager()
        await mgr.mark_read(
            test_session, conversation.id, users["user1"].id,
        )
        count = await mgr.get_unread_count(
            test_session, conversation.id, users["user1"].id,
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_unread_count_own_messages_excluded(
        self, test_session, users, conversation, messages,
    ):
        """User2's own messages don't count as unread for user2."""
        mgr = ReadReceiptManager()
        count = await mgr.get_unread_count(
            test_session, conversation.id, users["user2"].id,
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_unread_count_no_membership(
        self, test_session, conversation,
    ):
        mgr = ReadReceiptManager()
        count = await mgr.get_unread_count(
            test_session, conversation.id, uuid.uuid4(),
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_unread_count_pending_messages_excluded(
        self, test_session, users, conversation,
    ):
        """Pending (unmoderated) messages don't count as unread."""
        # Add a pending message
        pending_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            sender_id=users["user2"].id,
            content="Pending message",
            message_type="text",
            moderation_status="pending",
        )
        test_session.add(pending_msg)
        await test_session.flush()

        mgr = ReadReceiptManager()
        count = await mgr.get_unread_count(
            test_session, conversation.id, users["user1"].id,
        )
        # Only approved messages count — pending ones do not
        assert count == 0


# ---------------------------------------------------------------------------
# get_last_read
# ---------------------------------------------------------------------------


class TestGetLastRead:
    """Test get_last_read."""

    @pytest.mark.asyncio
    async def test_last_read_initially_none(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        last_read = await mgr.get_last_read(
            test_session, conversation.id, users["user1"].id,
        )
        assert last_read is None

    @pytest.mark.asyncio
    async def test_last_read_after_mark(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        ts = datetime(2026, 3, 20, 15, 0, 0, tzinfo=timezone.utc)
        await mgr.mark_read(
            test_session, conversation.id, users["user1"].id, read_at=ts,
        )
        last_read = await mgr.get_last_read(
            test_session, conversation.id, users["user1"].id,
        )
        # SQLite may strip tz info; compare as naive
        assert last_read is not None
        assert last_read.replace(tzinfo=None) == ts.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_last_read_unknown_user(
        self, test_session, conversation,
    ):
        mgr = ReadReceiptManager()
        last_read = await mgr.get_last_read(
            test_session, conversation.id, uuid.uuid4(),
        )
        assert last_read is None


# ---------------------------------------------------------------------------
# get_read_status
# ---------------------------------------------------------------------------


class TestGetReadStatus:
    """Test batch read status queries."""

    @pytest.mark.asyncio
    async def test_read_status_multiple_members(
        self, test_session, users, conversation,
    ):
        mgr = ReadReceiptManager()
        # Mark user1 as read
        ts = datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc)
        await mgr.mark_read(
            test_session, conversation.id, users["user1"].id, read_at=ts,
        )

        status = await mgr.get_read_status(
            test_session,
            conversation.id,
            [users["user1"].id, users["user2"].id],
        )
        assert str(users["user1"].id) in status
        assert str(users["user2"].id) in status
        # SQLite may strip tz info; compare as naive
        stored_ts = status[str(users["user1"].id)]
        assert stored_ts is not None
        assert stored_ts.replace(tzinfo=None) == ts.replace(tzinfo=None)
        assert status[str(users["user2"].id)] is None

    @pytest.mark.asyncio
    async def test_read_status_empty_list(
        self, test_session, conversation,
    ):
        mgr = ReadReceiptManager()
        status = await mgr.get_read_status(
            test_session, conversation.id, [],
        )
        assert status == {}


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------


class TestReceiptSingleton:
    """Test module-level singleton."""

    def test_receipt_manager_singleton_exists(self):
        from src.realtime.receipts import receipt_manager
        assert isinstance(receipt_manager, ReadReceiptManager)
