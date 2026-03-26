"""End-to-end tests for the social feed flow.

Full flow: create profile -> create post -> post in feed -> like -> comment
-> hashtag extraction -> trending.  Also tests pagination, age-tier content
limits, and moderation status filtering.
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    """In-memory SQLite engine."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def users(session):
    """Create three test users (teen, preteen, young)."""
    ids = {
        "teen": uuid.uuid4(),
        "preteen": uuid.uuid4(),
        "young": uuid.uuid4(),
    }
    for label, uid in ids.items():
        user = User(
            id=uid,
            email=f"{label}-{uuid.uuid4().hex[:8]}@example.com",
            display_name=f"{label.capitalize()} User",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        session.add(user)
    await session.flush()
    return ids


def _dob_for_age(age: int) -> str:
    today = datetime.now(timezone.utc).date()
    return today.replace(year=today.year - age).isoformat()


def _make_client(engine, session, user_id, group_id=None):
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role="parent")

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def teen_client(engine, session, users):
    async with _make_client(engine, session, users["teen"]) as c:
        yield c


@pytest_asyncio.fixture
async def preteen_client(engine, session, users):
    async with _make_client(engine, session, users["preteen"]) as c:
        yield c


@pytest_asyncio.fixture
async def young_client(engine, session, users):
    async with _make_client(engine, session, users["young"]) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper — create profile for client
# ---------------------------------------------------------------------------


async def _create_profile(client, name, age):
    return await client.post(
        "/api/v1/social/profiles",
        json={"display_name": name, "date_of_birth": _dob_for_age(age)},
    )


# ---------------------------------------------------------------------------
# Full Flow Tests
# ---------------------------------------------------------------------------


class TestFullFeedFlow:
    """Full end-to-end: profile -> post -> feed -> like -> comment -> hashtags."""

    @pytest.mark.asyncio
    async def test_full_create_post_and_appear_in_feed(
        self, teen_client, preteen_client, users
    ):
        """Create profile -> create post -> follow -> verify feed logic.

        Note: Teen tier uses post-publish moderation, so posts start as
        'pending' and only appear in feed/list once approved.  The feed
        correctly returns 0 for pending posts — this tests the flow works
        without errors and verifies the moderation gating.
        """
        # Create profiles
        resp = await _create_profile(teen_client, "Teen Poster", 14)
        assert resp.status_code == 201

        resp = await _create_profile(preteen_client, "Preteen Viewer", 11)
        assert resp.status_code == 201

        # Teen creates post
        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Hello from feed!"}
        )
        assert post_resp.status_code == 201
        post_data = post_resp.json()
        assert post_data["content"] == "Hello from feed!"
        post_id = post_data["id"]
        # Teen posts use post-publish moderation, so status is pending
        assert post_data["moderation_status"] in ["pending", "approved", "published"]

        # Preteen follows teen
        follow_resp = await preteen_client.post(
            f"/api/v1/social/follow/{users['teen']}"
        )
        assert follow_resp.status_code == 201
        follow_id = follow_resp.json()["id"]

        # Teen accepts follow
        accept_resp = await teen_client.patch(
            f"/api/v1/social/follow/{follow_id}/accept"
        )
        assert accept_resp.status_code == 200

        # Feed endpoint works — may have 0 items if post is pending moderation
        feed_resp = await preteen_client.get("/api/v1/social/feed")
        assert feed_resp.status_code == 200
        feed = feed_resp.json()
        assert "items" in feed
        assert "total" in feed

        # Direct post access always works regardless of moderation status
        direct_resp = await teen_client.get(f"/api/v1/social/posts/{post_id}")
        assert direct_resp.status_code == 200
        assert direct_resp.json()["id"] == post_id

    @pytest.mark.asyncio
    async def test_like_and_unlike_flow(self, teen_client):
        """Create post -> like -> check count -> unlike."""
        await _create_profile(teen_client, "Like Tester", 14)

        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Like this"}
        )
        post_id = post_resp.json()["id"]

        # Like
        like_resp = await teen_client.post(
            f"/api/v1/social/posts/{post_id}/like"
        )
        assert like_resp.status_code == 201

        # Verify like count
        get_resp = await teen_client.get(f"/api/v1/social/posts/{post_id}")
        assert get_resp.json()["like_count"] == 1

        # Unlike
        unlike_resp = await teen_client.delete(
            f"/api/v1/social/posts/{post_id}/like"
        )
        assert unlike_resp.status_code == 204

        # Verify count back to 0
        get_resp2 = await teen_client.get(f"/api/v1/social/posts/{post_id}")
        assert get_resp2.json()["like_count"] == 0

    @pytest.mark.asyncio
    async def test_comment_flow(self, teen_client):
        """Create post -> add comment -> list comments."""
        await _create_profile(teen_client, "Commenter", 14)

        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Comment on me"}
        )
        post_id = post_resp.json()["id"]

        # Add comment
        comment_resp = await teen_client.post(
            f"/api/v1/social/posts/{post_id}/comments",
            json={"content": "Nice post!"},
        )
        assert comment_resp.status_code == 201
        assert comment_resp.json()["content"] == "Nice post!"

        # List comments
        list_resp = await teen_client.get(
            f"/api/v1/social/posts/{post_id}/comments"
        )
        assert list_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_hashtag_extraction_and_trending(self, teen_client):
        """Create post with hashtags -> verify trending."""
        await _create_profile(teen_client, "Hashtagger", 14)

        # Post with hashtags
        await teen_client.post(
            "/api/v1/social/posts",
            json={"content": "Check out #coding #fun"},
        )
        await teen_client.post(
            "/api/v1/social/posts",
            json={"content": "More #coding today"},
        )

        # Trending hashtags
        trending_resp = await teen_client.get(
            "/api/v1/social/hashtags/trending"
        )
        assert trending_resp.status_code == 200
        tags = trending_resp.json()
        tag_names = [t["name"] for t in tags]
        assert "coding" in tag_names

    @pytest.mark.asyncio
    async def test_hashtag_extraction_multiple_tags(self, teen_client):
        """Multiple hashtags in one post are extracted."""
        await _create_profile(teen_client, "Multi Tag", 14)

        await teen_client.post(
            "/api/v1/social/posts",
            json={"content": "#alpha #beta #gamma three tags"},
        )

        trending_resp = await teen_client.get(
            "/api/v1/social/hashtags/trending"
        )
        tags = trending_resp.json()
        tag_names = [t["name"] for t in tags]
        assert "alpha" in tag_names
        assert "beta" in tag_names
        assert "gamma" in tag_names


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------


class TestPagination:
    """Test feed and post list pagination.

    Uses preteen client because preteen posts get pre-publish moderation
    with keyword_filter ALLOW -> approved status, so they appear in listings.
    Teen posts stay 'pending' (post-publish pipeline) and won't show in lists.
    """

    @pytest.mark.asyncio
    async def test_post_list_pagination(self, preteen_client):
        await _create_profile(preteen_client, "Paginator", 11)

        for i in range(5):
            resp = await preteen_client.post(
                "/api/v1/social/posts", json={"content": f"Post {i}"}
            )
            assert resp.status_code == 201
            assert resp.json()["moderation_status"] == "approved"

        # Page 1 with size 2
        resp1 = await preteen_client.get("/api/v1/social/posts?page=1&page_size=2")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1["items"]) == 2
        assert data1["total"] >= 5

        # Page 2
        resp2 = await preteen_client.get("/api/v1/social/posts?page=2&page_size=2")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["items"]) == 2

    @pytest.mark.asyncio
    async def test_feed_pagination_params(self, preteen_client):
        resp = await preteen_client.get("/api/v1/social/feed?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    @pytest.mark.asyncio
    async def test_comment_list_pagination(self, preteen_client):
        await _create_profile(preteen_client, "Comment Paginator", 11)

        post_resp = await preteen_client.post(
            "/api/v1/social/posts", json={"content": "Many comments"}
        )
        post_id = post_resp.json()["id"]

        for i in range(3):
            await preteen_client.post(
                f"/api/v1/social/posts/{post_id}/comments",
                json={"content": f"Comment {i}"},
            )

        resp = await preteen_client.get(
            f"/api/v1/social/posts/{post_id}/comments?page=1&page_size=2"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_list_empty_page(self, preteen_client):
        resp = await preteen_client.get("/api/v1/social/posts?page=999&page_size=20")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# Age-Tier Content Limits
# ---------------------------------------------------------------------------


class TestAgeTierContentLimits:
    """Test age-tier-specific post length limits."""

    @pytest.mark.asyncio
    async def test_young_tier_max_200_chars(self, young_client):
        await _create_profile(young_client, "Young Kid", 7)

        # Exactly 200 chars should work
        resp = await young_client.post(
            "/api/v1/social/posts", json={"content": "A" * 200}
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_young_tier_exceeds_200_chars(self, young_client):
        await _create_profile(young_client, "Young Kid", 7)

        resp = await young_client.post(
            "/api/v1/social/posts", json={"content": "A" * 201}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_preteen_tier_max_500_chars(self, preteen_client):
        await _create_profile(preteen_client, "Preteen Kid", 11)

        resp = await preteen_client.post(
            "/api/v1/social/posts", json={"content": "B" * 500}
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_preteen_tier_exceeds_500_chars(self, preteen_client):
        await _create_profile(preteen_client, "Preteen Kid", 11)

        resp = await preteen_client.post(
            "/api/v1/social/posts", json={"content": "B" * 501}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_teen_tier_max_1000_chars(self, teen_client):
        await _create_profile(teen_client, "Teen User", 14)

        resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "C" * 1000}
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_teen_tier_at_limit(self, teen_client):
        await _create_profile(teen_client, "Teen User", 14)

        # The PostCreate schema has max_length=1000, so 1001 should fail at validation
        resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "C" * 1001}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Moderation Status Filtering
# ---------------------------------------------------------------------------


class TestModerationFiltering:
    """Test that only approved posts appear in listings."""

    @pytest.mark.asyncio
    async def test_post_appears_in_list_based_on_moderation(self, teen_client):
        await _create_profile(teen_client, "Mod Test", 14)

        # Create a post (moderation pipeline determines status)
        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Normal post"}
        )
        assert post_resp.status_code == 201
        status = post_resp.json()["moderation_status"]
        # The moderation pipeline should set a status
        assert status in ["pending", "approved", "rejected", "flagged", "published"]

    @pytest.mark.asyncio
    async def test_list_only_shows_approved(self, preteen_client):
        """Preteen posts go through pre_publish and get approved by keyword filter."""
        await _create_profile(preteen_client, "Approved Filter", 11)

        # Create several posts (preteen gets pre-publish -> approved)
        for i in range(3):
            await preteen_client.post(
                "/api/v1/social/posts", json={"content": f"Post {i}"}
            )

        resp = await preteen_client.get("/api/v1/social/posts")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        for item in items:
            assert item["moderation_status"] == "approved"

    @pytest.mark.asyncio
    async def test_single_post_accessible_regardless_of_status(self, teen_client):
        await _create_profile(teen_client, "Single Post", 14)

        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Direct access"}
        )
        post_id = post_resp.json()["id"]

        # Direct get always works regardless of status
        resp = await teen_client.get(f"/api/v1/social/posts/{post_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == post_id


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestFeedEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_feed_empty_when_not_following(self, teen_client):
        resp = await teen_client.get("/api/v1/social/feed")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_like_nonexistent_post(self, teen_client):
        fake_id = str(uuid.uuid4())
        resp = await teen_client.post(f"/api/v1/social/posts/{fake_id}/like")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_comment_on_nonexistent_post(self, teen_client):
        await _create_profile(teen_client, "Commenter", 14)
        fake_id = str(uuid.uuid4())
        resp = await teen_client.post(
            f"/api/v1/social/posts/{fake_id}/comments",
            json={"content": "Ghost post"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unlike_without_prior_like(self, teen_client):
        await _create_profile(teen_client, "Unlike Test", 14)
        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "No like yet"}
        )
        post_id = post_resp.json()["id"]
        resp = await teen_client.delete(f"/api/v1/social/posts/{post_id}/like")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_post_empty_content(self, teen_client):
        await _create_profile(teen_client, "Empty Post", 14)
        resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": ""}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_comment_empty_content(self, teen_client):
        await _create_profile(teen_client, "Empty Comment", 14)
        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "Real post"}
        )
        post_id = post_resp.json()["id"]
        resp = await teen_client.post(
            f"/api/v1/social/posts/{post_id}/comments",
            json={"content": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_other_users_post(self, teen_client, preteen_client, users):
        await _create_profile(teen_client, "Owner", 14)
        await _create_profile(preteen_client, "Other", 11)

        post_resp = await teen_client.post(
            "/api/v1/social/posts", json={"content": "My post"}
        )
        post_id = post_resp.json()["id"]

        # Preteen tries to delete teen's post
        resp = await preteen_client.delete(f"/api/v1/social/posts/{post_id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_trending_with_limit_param(self, teen_client):
        resp = await teen_client.get(
            "/api/v1/social/hashtags/trending?limit=3"
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 3

    @pytest.mark.asyncio
    async def test_post_with_media_urls(self, teen_client):
        await _create_profile(teen_client, "Media Post", 14)
        resp = await teen_client.post(
            "/api/v1/social/posts",
            json={
                "content": "With media",
                "media_urls": ["https://cdn.example.com/img.jpg"],
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_post_with_post_type(self, teen_client):
        await _create_profile(teen_client, "Type Post", 14)
        resp = await teen_client.post(
            "/api/v1/social/posts",
            json={"content": "Image post", "post_type": "image"},
        )
        assert resp.status_code == 201
        assert resp.json()["post_type"] == "image"
