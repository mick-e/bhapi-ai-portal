"""End-to-end tests for the social module — HTTP endpoint tests."""

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
from src.social.models import Follow, Profile, SocialPost


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
    e2e_session.add_all([user1, user2])
    await e2e_session.flush()
    return {"user1": user1, "user2": user2}


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


def _dob_for_age(age: int) -> str:
    """Return ISO date string for a person of the given age."""
    today = datetime.now(timezone.utc).date()
    return today.replace(year=today.year - age).isoformat()


# ---------------------------------------------------------------------------
# Profile E2E tests
# ---------------------------------------------------------------------------


class TestProfileEndpoints:
    """Test profile CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_profile(self, client1):
        resp = await client1.post("/api/v1/social/profiles", json={
            "display_name": "Teen User",
            "date_of_birth": _dob_for_age(14),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Teen User"
        assert data["age_tier"] == "teen"

    @pytest.mark.asyncio
    async def test_create_profile_with_bio(self, client1):
        resp = await client1.post("/api/v1/social/profiles", json={
            "display_name": "Bio User",
            "bio": "Hello there",
            "date_of_birth": _dob_for_age(12),
        })
        assert resp.status_code == 201
        assert resp.json()["bio"] == "Hello there"

    @pytest.mark.asyncio
    async def test_get_my_profile(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "My Profile",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.get("/api/v1/social/profiles/me")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "My Profile"

    @pytest.mark.asyncio
    async def test_update_my_profile(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Original",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.put("/api/v1/social/profiles/me", json={
            "display_name": "Updated",
        })
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated"

    @pytest.mark.asyncio
    async def test_get_other_user_profile(self, client1, client2, e2e_users):
        await client2.post("/api/v1/social/profiles", json={
            "display_name": "User Two Profile",
            "date_of_birth": _dob_for_age(13),
        })
        resp = await client1.get(
            f"/api/v1/social/profiles/{e2e_users['user2'].id}"
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "User Two Profile"

    @pytest.mark.asyncio
    async def test_create_profile_invalid_age(self, client1):
        resp = await client1.post("/api/v1/social/profiles", json={
            "display_name": "Too Old",
            "date_of_birth": _dob_for_age(25),
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_profile_duplicate(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "First",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.post("/api/v1/social/profiles", json={
            "display_name": "Second",
            "date_of_birth": _dob_for_age(14),
        })
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Post E2E tests
# ---------------------------------------------------------------------------


class TestPostEndpoints:
    """Test post CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_post(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.post("/api/v1/social/posts", json={
            "content": "Hello world!",
        })
        assert resp.status_code == 201
        assert resp.json()["content"] == "Hello world!"

    @pytest.mark.asyncio
    async def test_create_post_no_profile(self, client1):
        resp = await client1.post("/api/v1/social/posts", json={
            "content": "No profile",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_post(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Get this post",
        })
        post_id = create_resp.json()["id"]
        resp = await client1.get(f"/api/v1/social/posts/{post_id}")
        assert resp.status_code == 200
        assert resp.json()["content"] == "Get this post"

    @pytest.mark.asyncio
    async def test_list_posts(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        await client1.post("/api/v1/social/posts", json={"content": "Post 1"})
        resp = await client1.get("/api/v1/social/posts")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_delete_post(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Delete me",
        })
        post_id = create_resp.json()["id"]
        resp = await client1.delete(f"/api/v1/social/posts/{post_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_like_post(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Like me",
        })
        post_id = create_resp.json()["id"]
        resp = await client1.post(f"/api/v1/social/posts/{post_id}/like")
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_unlike_post(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Unlike me",
        })
        post_id = create_resp.json()["id"]
        await client1.post(f"/api/v1/social/posts/{post_id}/like")
        resp = await client1.delete(f"/api/v1/social/posts/{post_id}/like")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_add_comment(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Comment on me",
        })
        post_id = create_resp.json()["id"]
        resp = await client1.post(
            f"/api/v1/social/posts/{post_id}/comments",
            json={"content": "Great post!"},
        )
        assert resp.status_code == 201
        assert resp.json()["content"] == "Great post!"

    @pytest.mark.asyncio
    async def test_list_comments(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Poster",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Post with comments",
        })
        post_id = create_resp.json()["id"]
        resp = await client1.get(f"/api/v1/social/posts/{post_id}/comments")
        assert resp.status_code == 200
        assert "items" in resp.json()


# ---------------------------------------------------------------------------
# Follow E2E tests
# ---------------------------------------------------------------------------


class TestFollowEndpoints:
    """Test follow/unfollow endpoints."""

    @pytest.mark.asyncio
    async def test_follow_user(self, client1, e2e_users):
        resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    @pytest.mark.asyncio
    async def test_accept_follow(self, client1, client2, e2e_users):
        follow_resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        follow_id = follow_resp.json()["id"]
        resp = await client2.patch(
            f"/api/v1/social/follow/{follow_id}/accept"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_unfollow_user(self, client1, e2e_users):
        await client1.post(f"/api/v1/social/follow/{e2e_users['user2'].id}")
        resp = await client1.delete(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_list_followers(self, client1, client2, e2e_users):
        follow_resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        follow_id = follow_resp.json()["id"]
        await client2.patch(f"/api/v1/social/follow/{follow_id}/accept")
        resp = await client2.get("/api/v1/social/followers")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_following(self, client1, client2, e2e_users):
        follow_resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        follow_id = follow_resp.json()["id"]
        await client2.patch(f"/api/v1/social/follow/{follow_id}/accept")
        resp = await client1.get("/api/v1/social/following")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_follow_self_rejected(self, client1, e2e_users):
        resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user1'].id}"
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_follow_duplicate_rejected(self, client1, e2e_users):
        await client1.post(f"/api/v1/social/follow/{e2e_users['user2'].id}")
        resp = await client1.post(
            f"/api/v1/social/follow/{e2e_users['user2'].id}"
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Feed E2E tests
# ---------------------------------------------------------------------------


class TestFeedEndpoints:
    """Test feed endpoint."""

    @pytest.mark.asyncio
    async def test_feed_empty(self, client1):
        resp = await client1.get("/api/v1/social/feed")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_feed_pagination(self, client1):
        resp = await client1.get("/api/v1/social/feed?page=1&page_size=5")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Hashtag E2E tests
# ---------------------------------------------------------------------------


class TestHashtagEndpoints:
    """Test hashtag endpoints."""

    @pytest.mark.asyncio
    async def test_trending_hashtags_empty(self, client1):
        resp = await client1.get("/api/v1/social/hashtags/trending")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_trending_hashtags_with_limit(self, client1):
        resp = await client1.get("/api/v1/social/hashtags/trending?limit=5")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Additional E2E tests for coverage
# ---------------------------------------------------------------------------


class TestAdditionalEndpoints:
    """Additional E2E tests for edge cases."""

    @pytest.mark.asyncio
    async def test_create_post_with_hashtags(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Hashtag User",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.post("/api/v1/social/posts", json={
            "content": "Hello #world #test",
        })
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_update_profile_bio_and_visibility(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Update Test",
            "date_of_birth": _dob_for_age(14),
        })
        resp = await client1.put("/api/v1/social/profiles/me", json={
            "bio": "New bio text",
            "visibility": "public",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["bio"] == "New bio text"
        assert data["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, client1):
        fake_id = str(uuid.uuid4())
        resp = await client1.get(f"/api/v1/social/profiles/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_post(self, client1):
        fake_id = str(uuid.uuid4())
        resp = await client1.get(f"/api/v1/social/posts/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_like_post_duplicate(self, client1):
        await client1.post("/api/v1/social/profiles", json={
            "display_name": "Like Test",
            "date_of_birth": _dob_for_age(14),
        })
        create_resp = await client1.post("/api/v1/social/posts", json={
            "content": "Double like",
        })
        post_id = create_resp.json()["id"]
        await client1.post(f"/api/v1/social/posts/{post_id}/like")
        resp = await client1.post(f"/api/v1/social/posts/{post_id}/like")
        assert resp.status_code == 409
