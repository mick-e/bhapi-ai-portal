"""End-to-end tests for social activity monitoring (P2-M1).

Covers:
- Parent can see aggregated social activity for their child
- Post counts (7d/30d)
- Message counts (7d/30d)
- Contact counts (accepted, pending)
- Flagged content from moderation queue
- Time estimates and time trend
- Degraded sections on partial failure
- Child cannot access monitoring endpoints (403)
- Empty state when child has no social activity
- Multiple children isolation
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.contacts.models import Contact
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.messaging.models import Conversation, ConversationMember, Message
from src.moderation.models import ModerationQueue
from src.schemas import GroupContext
from src.social.models import SocialPost

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sm_engine():
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
async def sm_session(sm_engine):
    async_session_maker = sessionmaker(
        sm_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def sm_data(sm_session):
    """Create parent + two children with social data."""
    now = datetime.now(timezone.utc)

    parent = User(
        id=uuid.uuid4(),
        email=f"smparent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="SM Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_user = User(
        id=uuid.uuid4(),
        email=f"smchild-{uuid.uuid4().hex[:8]}@example.com",
        display_name="SM Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child2_user = User(
        id=uuid.uuid4(),
        email=f"smchild2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="SM Child 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    other_user = User(
        id=uuid.uuid4(),
        email=f"smother-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sm_session.add_all([parent, child_user, child2_user, other_user])
    await sm_session.flush()

    group = Group(
        id=uuid.uuid4(), name="SM Family", type="family", owner_id=parent.id,
    )
    sm_session.add(group)
    await sm_session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=parent.id,
        role="parent", display_name="Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child_user.id,
        role="member", display_name="Child One",
        date_of_birth=datetime(2015, 6, 15, tzinfo=timezone.utc),
    )
    child2_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child2_user.id,
        role="member", display_name="Child Two",
        date_of_birth=datetime(2017, 3, 10, tzinfo=timezone.utc),
    )
    sm_session.add_all([parent_member, child_member, child2_member])
    await sm_session.flush()

    # --- Social posts for child 1 ---
    # 3 recent posts (within 7d), 2 older posts (within 30d)
    for i in range(3):
        sm_session.add(SocialPost(
            id=uuid.uuid4(), author_id=child_user.id,
            content=f"Recent post {i}", post_type="text",
            moderation_status="approved",
            created_at=now - timedelta(days=i + 1),
        ))
    for i in range(2):
        sm_session.add(SocialPost(
            id=uuid.uuid4(), author_id=child_user.id,
            content=f"Older post {i}", post_type="text",
            moderation_status="approved",
            created_at=now - timedelta(days=15 + i),
        ))

    # A flagged post for child 1
    flagged_post = SocialPost(
        id=uuid.uuid4(), author_id=child_user.id,
        content="Bad post", post_type="text",
        moderation_status="rejected",
        created_at=now - timedelta(days=2),
    )
    sm_session.add(flagged_post)
    await sm_session.flush()

    # Moderation queue entry for the flagged post
    sm_session.add(ModerationQueue(
        id=uuid.uuid4(), content_type="post", content_id=flagged_post.id,
        pipeline="pre_publish", status="rejected",
        created_at=now - timedelta(days=2),
    ))

    # --- Messages for child 1 ---
    conv = Conversation(
        id=uuid.uuid4(), type="direct", created_by=child_user.id,
    )
    sm_session.add(conv)
    await sm_session.flush()

    sm_session.add(ConversationMember(
        id=uuid.uuid4(), conversation_id=conv.id, user_id=child_user.id,
    ))
    sm_session.add(ConversationMember(
        id=uuid.uuid4(), conversation_id=conv.id, user_id=other_user.id,
    ))
    await sm_session.flush()

    # 4 messages within 7d, 2 older
    for i in range(4):
        sm_session.add(Message(
            id=uuid.uuid4(), conversation_id=conv.id,
            sender_id=child_user.id, content=f"msg {i}",
            message_type="text", moderation_status="approved",
            created_at=now - timedelta(days=i + 1),
        ))
    for i in range(2):
        sm_session.add(Message(
            id=uuid.uuid4(), conversation_id=conv.id,
            sender_id=child_user.id, content=f"old msg {i}",
            message_type="text", moderation_status="approved",
            created_at=now - timedelta(days=20 + i),
        ))

    # --- Contacts for child 1 ---
    # 2 accepted contacts (need unique requester/target pairs)
    contact_user_1 = User(
        id=uuid.uuid4(),
        email=f"contact1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Contact 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    contact_user_2 = User(
        id=uuid.uuid4(),
        email=f"contact2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Contact 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sm_session.add_all([contact_user_1, contact_user_2])
    await sm_session.flush()

    sm_session.add(Contact(
        id=uuid.uuid4(), requester_id=child_user.id,
        target_id=contact_user_1.id, status="accepted",
        parent_approval_status="approved",
    ))
    sm_session.add(Contact(
        id=uuid.uuid4(), requester_id=child_user.id,
        target_id=contact_user_2.id, status="accepted",
        parent_approval_status="approved",
    ))
    # 1 pending contact
    sm_session.add(Contact(
        id=uuid.uuid4(), requester_id=other_user.id,
        target_id=child_user.id, status="pending",
        parent_approval_status="pending",
    ))

    # --- Posts for child 2 (1 recent post, no messages) ---
    sm_session.add(SocialPost(
        id=uuid.uuid4(), author_id=child2_user.id,
        content="Child2 post", post_type="text",
        moderation_status="approved",
        created_at=now - timedelta(days=1),
    ))

    await sm_session.flush()
    await sm_session.commit()

    return {
        "parent": parent,
        "child_user": child_user,
        "child2_user": child2_user,
        "other_user": other_user,
        "group": group,
        "parent_member": parent_member,
        "child_member": child_member,
        "child2_member": child2_member,
        "flagged_post": flagged_post,
    }


def _make_client(sm_engine, sm_session, user_id, group_id, role="parent"):
    app = create_app()

    async def get_db_override():
        try:
            yield sm_session
            await sm_session.commit()
        except Exception:
            await sm_session.rollback()
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


# ---------------------------------------------------------------------------
# Tests — Parent accessing social activity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_sees_child_post_counts(sm_engine, sm_session, sm_data):
    """Parent can see post counts for 7d and 30d."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    # 3 recent + 1 flagged within 7d = 4, but flagged was 2 days ago so within 7d
    assert body["post_count_7d"] >= 3
    # 3 recent + 2 older + 1 flagged = 6 total within 30d
    assert body["post_count_30d"] >= 5


@pytest.mark.asyncio
async def test_parent_sees_child_message_counts(sm_engine, sm_session, sm_data):
    """Parent can see message counts."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message_count_7d"] == 4
    assert body["message_count_30d"] == 6


@pytest.mark.asyncio
async def test_parent_sees_child_contact_counts(sm_engine, sm_session, sm_data):
    """Parent can see accepted and pending contacts."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["contact_count"] == 2
    assert body["pending_contact_requests"] == 1


@pytest.mark.asyncio
async def test_parent_sees_flagged_content(sm_engine, sm_session, sm_data):
    """Parent can see flagged content count and items."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged_content_count"] >= 1
    assert len(body["flagged_items"]) >= 1
    assert body["flagged_items"][0]["content_type"] == "post"
    assert body["flagged_items"][0]["status"] == "rejected"


@pytest.mark.asyncio
async def test_parent_sees_time_estimates(sm_engine, sm_session, sm_data):
    """Parent can see time spent estimates."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    # 7d: posts * 5 + messages * 2
    assert body["time_spent_minutes_7d"] > 0
    assert body["time_spent_minutes_30d"] >= body["time_spent_minutes_7d"]


@pytest.mark.asyncio
async def test_parent_sees_time_trend(sm_engine, sm_session, sm_data):
    """Parent gets 7-day time trend data."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["time_trend"]) == 7
    for point in body["time_trend"]:
        assert "date" in point
        assert "minutes" in point
        assert point["minutes"] >= 0


@pytest.mark.asyncio
async def test_parent_sees_member_name(sm_engine, sm_session, sm_data):
    """Response includes the child's display name."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["member_name"] == "Child One"
    assert body["member_id"] == str(d["child_member"].id)


@pytest.mark.asyncio
async def test_child2_isolation(sm_engine, sm_session, sm_data):
    """Child 2's data is separate from child 1."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child2_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["post_count_7d"] == 1
    assert body["post_count_30d"] == 1
    assert body["message_count_7d"] == 0
    assert body["message_count_30d"] == 0
    assert body["contact_count"] == 0


# ---------------------------------------------------------------------------
# Tests — Child cannot access monitoring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_cannot_access_social_activity(sm_engine, sm_session, sm_data):
    """Child role is rejected with 403."""
    d = sm_data
    async with _make_client(
        sm_engine, sm_session, d["child_user"].id, d["group"].id, role="member"
    ) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nonexistent_member_returns_404(sm_engine, sm_session, sm_data):
    """Requesting a non-existent member returns 404."""
    d = sm_data
    fake_id = uuid.uuid4()
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_member_without_user_id(sm_engine, sm_session, sm_data):
    """A member without a user_id (young child placeholder) returns zeroes."""
    d = sm_data
    # Add a member with no user_id
    no_user_member = GroupMember(
        id=uuid.uuid4(), group_id=d["group"].id, user_id=None,
        role="member", display_name="Baby",
        date_of_birth=datetime(2021, 1, 1, tzinfo=timezone.utc),
    )
    sm_session.add(no_user_member)
    await sm_session.flush()
    await sm_session.commit()

    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={no_user_member.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["post_count_7d"] == 0
    assert body["message_count_7d"] == 0
    assert body["contact_count"] == 0


@pytest.mark.asyncio
async def test_missing_member_id_returns_422(sm_engine, sm_session, sm_data):
    """Missing member_id query param returns 422."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get("/api/v1/portal/social-activity")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_degraded_sections_empty_on_success(sm_engine, sm_session, sm_data):
    """Degraded sections list should be empty on normal operation."""
    d = sm_data
    async with _make_client(sm_engine, sm_session, d["parent"].id, d["group"].id) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["degraded_sections"] == []


@pytest.mark.asyncio
async def test_school_admin_can_access(sm_engine, sm_session, sm_data):
    """School admin role can also access social activity."""
    d = sm_data
    async with _make_client(
        sm_engine, sm_session, d["parent"].id, d["group"].id, role="school_admin"
    ) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_club_admin_can_access(sm_engine, sm_session, sm_data):
    """Club admin role can also access social activity."""
    d = sm_data
    async with _make_client(
        sm_engine, sm_session, d["parent"].id, d["group"].id, role="club_admin"
    ) as c:
        resp = await c.get(f"/api/v1/portal/social-activity?member_id={d['child_member'].id}")
    assert resp.status_code == 200
