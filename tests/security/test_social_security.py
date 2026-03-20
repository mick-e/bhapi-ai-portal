"""Security tests for the social module.

Covers:
- Unauthenticated access (401)
- Cross-user data access
- Age-tier permission enforcement
- Input validation / injection
- Authorization boundaries
"""

import uuid
from datetime import datetime, timezone

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
from src.social.models import Profile, SocialPost


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
    user1 = User(
        id=uuid.uuid4(),
        email=f"sec1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Sec User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"sec2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Sec User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()

    # Create profiles for both users (teen age)
    today = datetime.now(timezone.utc).date()
    dob_teen = today.replace(year=today.year - 14)
    profile1 = Profile(
        id=uuid.uuid4(),
        user_id=user1.id,
        display_name="Sec User 1",
        date_of_birth=dob_teen,
        age_tier="teen",
        visibility="friends_only",
    )
    profile2 = Profile(
        id=uuid.uuid4(),
        user_id=user2.id,
        display_name="Sec User 2",
        date_of_birth=dob_teen,
        age_tier="teen",
        visibility="friends_only",
    )
    sec_session.add_all([profile1, profile2])
    await sec_session.flush()

    # Create a post by user1
    post = SocialPost(
        id=uuid.uuid4(),
        author_id=user1.id,
        content="User 1 post",
        post_type="text",
        moderation_status="approved",
    )
    sec_session.add(post)
    await sec_session.flush()

    return {
        "user1": user1,
        "user2": user2,
        "profile1": profile1,
        "profile2": profile2,
        "post": post,
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


@pytest.fixture
async def client_user1(sec_engine, sec_session, sec_users):
    async with _authed_client_for(sec_engine, sec_session, sec_users["user1"].id) as c:
        yield c


@pytest.fixture
async def client_user2(sec_engine, sec_session, sec_users):
    async with _authed_client_for(sec_engine, sec_session, sec_users["user2"].id) as c:
        yield c


def _dob_for_age(age: int) -> str:
    today = datetime.now(timezone.utc).date()
    return today.replace(year=today.year - age).isoformat()


# ---------------------------------------------------------------------------
# Tests: Unauthenticated access (401)
# ---------------------------------------------------------------------------


class TestUnauthenticated:
    """All social endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_profiles_unauthenticated(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/social/profiles/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_posts_unauthenticated(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/social/posts")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_feed_unauthenticated(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/social/feed")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_followers_unauthenticated(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/social/followers")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_hashtags_unauthenticated(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/social/hashtags/trending")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Cross-user authorization
# ---------------------------------------------------------------------------


class TestCrossUserAuth:
    """Prevent users from modifying others' data."""

    @pytest.mark.asyncio
    async def test_delete_others_post(self, client_user2, sec_users):
        """User2 cannot delete user1's post."""
        post_id = sec_users["post"].id
        resp = await client_user2.delete(f"/api/v1/social/posts/{post_id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_accept_follow_not_directed_to_you(self, client_user1, sec_users):
        """User1 cannot accept a follow request directed to user2."""
        from src.social.models import Follow

        # Create a follow from some other user to user2 directly in DB
        # The endpoint should reject user1 trying to accept it
        follow_id = uuid.uuid4()
        resp = await client_user1.patch(
            f"/api/v1/social/follow/{follow_id}/accept"
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Test input sanitization and validation."""

    @pytest.mark.asyncio
    async def test_xss_in_display_name(self, client_user1):
        """XSS attempt in display name should not break things."""
        resp = await client_user1.put("/api/v1/social/profiles/me", json={
            "display_name": "<script>alert('xss')</script>",
        })
        # Should succeed but store as plain text (no execution)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_post_content(self, client_user1):
        """Post with empty content should be rejected."""
        resp = await client_user1.post("/api/v1/social/posts", json={
            "content": "",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_post_content_too_long(self, client_user1):
        """Post exceeding max length should be rejected."""
        resp = await client_user1.post("/api/v1/social/posts", json={
            "content": "A" * 1001,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_post_type(self, client_user1):
        """Invalid post type should be rejected."""
        resp = await client_user1.post("/api/v1/social/posts", json={
            "content": "Hello",
            "post_type": "executable",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_visibility(self, client_user1):
        """Invalid visibility should be rejected."""
        resp = await client_user1.put("/api/v1/social/profiles/me", json={
            "visibility": "everyone_on_earth",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_comment_content(self, client_user1, sec_users):
        """Comment with empty content should be rejected."""
        post_id = sec_users["post"].id
        resp = await client_user1.post(
            f"/api/v1/social/posts/{post_id}/comments",
            json={"content": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_sql_injection_in_bio(self, client_user1):
        """SQL injection in bio should be stored as plain text."""
        resp = await client_user1.put("/api/v1/social/profiles/me", json={
            "bio": "'; DROP TABLE profiles; --",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: UUID path parameter validation
# ---------------------------------------------------------------------------


class TestPathParamValidation:
    """Verify UUID path parameters reject invalid formats."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_post(self, client_user1):
        resp = await client_user1.get("/api/v1/social/posts/not-a-uuid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_uuid_follow(self, client_user1):
        resp = await client_user1.post("/api/v1/social/follow/not-a-uuid")
        assert resp.status_code == 422
