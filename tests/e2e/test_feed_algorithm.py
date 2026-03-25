"""E2E tests for the engagement-weighted feed algorithm (Task 6 — P2-S2).

Covers:
- chronological ordering (newest first)
- engagement ordering (likes + comments + recency decay)
- likes rank a post higher than a newer post with no likes
- comments worth 3x likes in ranking
- old posts decay relative to newer posts
- invalid algorithm param returns 422
- pagination works for both algorithms
- only approved posts are returned
- empty feed returns empty list
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
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext
from src.social.models import Follow, PostComment, PostLike, Profile, SocialPost


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def engine():
    """In-memory SQLite engine with FK enforcement."""
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
async def test_session(engine):
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


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


def _dob_for_age(age: int) -> str:
    today = datetime.now(timezone.utc).date()
    return today.replace(year=today.year - age).isoformat()


async def _create_user_and_profile(session, age: int, suffix: str | None = None) -> tuple[uuid.UUID, str]:
    """Create a User row and a social Profile; return (user_id, age_tier)."""
    from src.age_tier import age_from_dob, get_tier_for_age
    from datetime import date

    uid = uuid.uuid4()
    label = suffix or uid.hex[:8]
    user = User(
        id=uid,
        email=f"user-{label}@example.com",
        display_name=f"User {label}",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    today = datetime.now(timezone.utc).date()
    dob = today.replace(year=today.year - age)
    tier = get_tier_for_age(age_from_dob(dob))
    profile = Profile(
        id=uuid.uuid4(),
        user_id=uid,
        display_name=f"User {label}",
        date_of_birth=dob,
        age_tier=tier.value,
        visibility="public",
    )
    session.add(profile)
    await session.flush()

    return uid, tier.value


async def _make_approved_post(
    session,
    author_id: uuid.UUID,
    content: str,
    created_at: datetime | None = None,
) -> SocialPost:
    """Insert a SocialPost directly with moderation_status='approved'."""
    post = SocialPost(
        id=uuid.uuid4(),
        author_id=author_id,
        content=content,
        post_type="text",
        moderation_status="approved",
    )
    if created_at is not None:
        post.created_at = created_at
    session.add(post)
    await session.flush()
    return post


async def _accept_follow(session, follower_id: uuid.UUID, following_id: uuid.UUID) -> None:
    """Create an accepted Follow relationship directly in DB."""
    follow = Follow(
        id=uuid.uuid4(),
        follower_id=follower_id,
        following_id=following_id,
        status="accepted",
    )
    session.add(follow)
    await session.flush()


async def _add_likes(session, post_id: uuid.UUID, count: int) -> None:
    """Add `count` PostLike rows for a post (create real User rows for each liker)."""
    for i in range(count):
        liker_id = uuid.uuid4()
        liker = User(
            id=liker_id,
            email=f"liker-{liker_id.hex[:8]}@example.com",
            display_name=f"Liker {i}",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        session.add(liker)
        await session.flush()
        like = PostLike(
            id=uuid.uuid4(),
            post_id=post_id,
            user_id=liker_id,
        )
        session.add(like)
    await session.flush()


async def _add_comments(session, post_id: uuid.UUID, author_id: uuid.UUID, count: int) -> None:
    """Add `count` PostComment rows (approved) for a post."""
    for i in range(count):
        comment = PostComment(
            id=uuid.uuid4(),
            post_id=post_id,
            author_id=author_id,
            content=f"comment {i}",
            moderation_status="approved",
        )
        session.add(comment)
    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChronologicalFeed:
    """Chronological algorithm tests."""

    @pytest.mark.asyncio
    async def test_chronological_returns_newest_first(self, engine, test_session):
        """Feed with algorithm=chronological returns posts newest first."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-c1")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-c1")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        old_post = await _make_approved_post(
            test_session, poster_id, "Older post", created_at=now - timedelta(hours=5)
        )
        new_post = await _make_approved_post(
            test_session, poster_id, "Newer post", created_at=now - timedelta(hours=1)
        )

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=chronological")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Newest first
        assert items[0]["id"] == str(new_post.id)
        assert items[1]["id"] == str(old_post.id)

    @pytest.mark.asyncio
    async def test_chronological_default_when_no_algorithm_param(self, engine, test_session):
        """Default feed (no algorithm param) behaves as chronological."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-c2")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-c2")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        await _make_approved_post(
            test_session, poster_id, "First post", created_at=now - timedelta(hours=3)
        )
        await _make_approved_post(
            test_session, poster_id, "Second post", created_at=now - timedelta(hours=1)
        )

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Second post (more recent) should be first
        assert items[0]["content"] == "Second post"

    @pytest.mark.asyncio
    async def test_chronological_empty_feed_returns_empty_list(self, engine, test_session):
        """User with no follows returns empty feed."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-c3")

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=chronological")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestEngagementFeed:
    """Engagement algorithm tests."""

    @pytest.mark.asyncio
    async def test_engagement_feed_returns_200(self, engine, test_session):
        """Engagement algorithm endpoint returns 200."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e1")

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_with_more_likes_ranks_higher_than_newer_post(self, engine, test_session):
        """Post with likes ranks higher than newer post with no likes."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e2")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-e2")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        # Older post with many likes
        liked_post = await _make_approved_post(
            test_session, poster_id, "Old popular post", created_at=now - timedelta(hours=6)
        )
        await _add_likes(test_session, liked_post.id, count=20)

        # Newer post with no likes
        await _make_approved_post(
            test_session, poster_id, "New plain post", created_at=now - timedelta(hours=1)
        )

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # The popular (liked) post should rank first despite being older
        assert items[0]["id"] == str(liked_post.id)

    @pytest.mark.asyncio
    async def test_comments_worth_3x_likes_in_ranking(self, engine, test_session):
        """Post with 1 comment outranks a post with 2 likes (comments score 3x)."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e3")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-e3")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        # Post with 1 comment (score contribution = 3.0) — same age
        commented_post = await _make_approved_post(
            test_session, poster_id, "Commented post", created_at=now - timedelta(hours=2)
        )
        await _add_comments(test_session, commented_post.id, poster_id, count=1)

        # Post with 2 likes (score contribution = 2.0) — same age
        liked_post = await _make_approved_post(
            test_session, poster_id, "Liked post", created_at=now - timedelta(hours=2)
        )
        await _add_likes(test_session, liked_post.id, count=2)

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Commented post should rank higher (3 > 2)
        assert items[0]["id"] == str(commented_post.id)

    @pytest.mark.asyncio
    async def test_old_posts_decay_in_ranking(self, engine, test_session):
        """A very old post with moderate likes ranks lower than a fresh post with fewer likes."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e4")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-e4")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        # Very old post (>48h, so recency_factor = 0.1) with 5 likes: score = (5+1)*0.1 = 0.6
        old_post = await _make_approved_post(
            test_session, poster_id, "Ancient post", created_at=now - timedelta(hours=96)
        )
        await _add_likes(test_session, old_post.id, count=5)

        # Fresh post (1h old, recency_factor ~0.979) with 0 likes: score = (0+1)*0.979 = 0.979
        fresh_post = await _make_approved_post(
            test_session, poster_id, "Fresh post", created_at=now - timedelta(hours=1)
        )

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Fresh post ranks higher despite fewer likes because old post is decayed
        assert items[0]["id"] == str(fresh_post.id)

    @pytest.mark.asyncio
    async def test_engagement_feed_only_returns_approved_posts(self, engine, test_session):
        """Engagement feed excludes pending/rejected posts."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e5")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-e5")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        # Approved post
        approved = await _make_approved_post(test_session, poster_id, "Approved post")

        # Pending post (should not appear)
        pending = SocialPost(
            id=uuid.uuid4(),
            author_id=poster_id,
            content="Pending post",
            post_type="text",
            moderation_status="pending",
        )
        test_session.add(pending)
        await test_session.flush()

        # Rejected post (should not appear)
        rejected = SocialPost(
            id=uuid.uuid4(),
            author_id=poster_id,
            content="Rejected post",
            post_type="text",
            moderation_status="rejected",
        )
        test_session.add(rejected)
        await test_session.flush()

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == str(approved.id)
        # Non-approved posts must not appear
        returned_ids = {item["id"] for item in items}
        assert str(pending.id) not in returned_ids
        assert str(rejected.id) not in returned_ids

    @pytest.mark.asyncio
    async def test_engagement_feed_empty_when_not_following(self, engine, test_session):
        """User with no accepted follows gets empty engagement feed."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e6")

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_engagement_feed_response_includes_like_and_comment_counts(
        self, engine, test_session
    ):
        """Engagement feed items include like_count and comment_count fields."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-e7")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-e7")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        post = await _make_approved_post(test_session, poster_id, "Engaged post")
        await _add_likes(test_session, post.id, count=3)
        await _add_comments(test_session, post.id, poster_id, count=2)

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=engagement")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["like_count"] == 3
        assert items[0]["comment_count"] == 2


class TestFeedPagination:
    """Pagination works for both algorithms."""

    @pytest.mark.asyncio
    async def test_chronological_feed_pagination(self, engine, test_session):
        """Chronological feed respects offset and limit via page/page_size."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-p1")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-p1")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        for i in range(5):
            await _make_approved_post(
                test_session,
                poster_id,
                f"Post {i}",
                created_at=now - timedelta(hours=i + 1),
            )

        async with _make_client(engine, test_session, viewer_id) as client:
            page1 = await client.get(
                "/api/v1/social/feed?algorithm=chronological&page=1&page_size=3"
            )
            page2 = await client.get(
                "/api/v1/social/feed?algorithm=chronological&page=2&page_size=3"
            )

        assert page1.status_code == 200
        assert page2.status_code == 200
        assert len(page1.json()["items"]) == 3
        assert len(page2.json()["items"]) == 2
        assert page1.json()["total"] == 5
        # No overlap between pages
        ids_p1 = {item["id"] for item in page1.json()["items"]}
        ids_p2 = {item["id"] for item in page2.json()["items"]}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_engagement_feed_pagination(self, engine, test_session):
        """Engagement feed respects page/page_size."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-p2")
        poster_id, _ = await _create_user_and_profile(test_session, age=14, suffix="poster-p2")
        await _accept_follow(test_session, follower_id=viewer_id, following_id=poster_id)

        now = datetime.now(timezone.utc)
        for i in range(4):
            post = await _make_approved_post(
                test_session,
                poster_id,
                f"Post {i}",
                created_at=now - timedelta(hours=i + 1),
            )
            await _add_likes(test_session, post.id, count=i)

        async with _make_client(engine, test_session, viewer_id) as client:
            page1 = await client.get(
                "/api/v1/social/feed?algorithm=engagement&page=1&page_size=2"
            )
            page2 = await client.get(
                "/api/v1/social/feed?algorithm=engagement&page=2&page_size=2"
            )

        assert page1.status_code == 200
        assert page2.status_code == 200
        assert len(page1.json()["items"]) == 2
        assert len(page2.json()["items"]) == 2
        assert page1.json()["total"] == 4
        # No overlap
        ids_p1 = {item["id"] for item in page1.json()["items"]}
        ids_p2 = {item["id"] for item in page2.json()["items"]}
        assert ids_p1.isdisjoint(ids_p2)


class TestInvalidAlgorithmParam:
    """Validation of the algorithm query parameter."""

    @pytest.mark.asyncio
    async def test_invalid_algorithm_returns_422(self, engine, test_session):
        """Invalid algorithm value returns 422 Unprocessable Entity."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-v1")

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=random")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_algorithm_variant_returns_422(self, engine, test_session):
        """Algorithm values not in the allowed set return 422."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-v2")

        async with _make_client(engine, test_session, viewer_id) as client:
            resp = await client.get("/api/v1/social/feed?algorithm=trending")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_algorithms_do_not_return_422(self, engine, test_session):
        """Both 'chronological' and 'engagement' are valid algorithm values."""
        viewer_id, _ = await _create_user_and_profile(test_session, age=14, suffix="viewer-v3")

        async with _make_client(engine, test_session, viewer_id) as client:
            r1 = await client.get("/api/v1/social/feed?algorithm=chronological")
            r2 = await client.get("/api/v1/social/feed?algorithm=engagement")

        assert r1.status_code == 200
        assert r2.status_code == 200
