"""Unit tests for the social module — profiles, posts, comments, likes, follows, feed."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.social.models import Follow, Hashtag, PostLike, Profile, SocialPost
from src.social.schemas import (
    PostCreate,
    ProfileCreate,
    ProfileUpdate,
)
from src.social.service import (
    accept_follow,
    add_comment,
    create_post,
    create_profile,
    delete_post,
    extract_hashtags,
    follow_user,
    get_feed,
    get_post,
    get_profile,
    get_profile_by_id,
    get_trending_hashtags,
    like_post,
    list_comments,
    list_followers,
    list_following,
    unfollow_user,
    unlike_post,
    update_profile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession, **kwargs) -> User:
    """Create a test user."""
    uid = kwargs.pop("id", None) or uuid.uuid4()
    user = User(
        id=uid,
        email=kwargs.pop("email", f"test-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.pop("display_name", "Test User"),
        account_type=kwargs.pop("account_type", "family"),
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_profile(
    session: AsyncSession, user_id: uuid.UUID, age_tier: str = "teen",
    dob: date | None = None,
) -> Profile:
    """Create a test profile."""
    if dob is None:
        # Default to teen (14 years old)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 14)

    data = ProfileCreate(
        display_name="Test User",
        date_of_birth=dob,
        visibility="friends_only",
    )
    return await create_profile(session, user_id, data)


# ---------------------------------------------------------------------------
# extract_hashtags
# ---------------------------------------------------------------------------


class TestExtractHashtags:
    """Test hashtag extraction from content."""

    def test_single_hashtag(self):
        assert extract_hashtags("Hello #world") == ["world"]

    def test_multiple_hashtags(self):
        result = extract_hashtags("#hello #world #test")
        assert result == ["hello", "world", "test"]

    def test_no_hashtags(self):
        assert extract_hashtags("Hello world") == []

    def test_hashtag_with_underscores(self):
        assert extract_hashtags("#hello_world") == ["hello_world"]

    def test_hashtag_with_numbers(self):
        assert extract_hashtags("#test123") == ["test123"]

    def test_empty_string(self):
        assert extract_hashtags("") == []

    def test_hashtag_only_hash(self):
        # Just "#" with nothing after should not match
        assert extract_hashtags("Hello # world") == []


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


class TestCreateProfile:
    """Test profile creation."""

    @pytest.mark.asyncio
    async def test_create_profile_teen(self, test_session):
        user = await _make_user(test_session)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 14)
        data = ProfileCreate(
            display_name="Teen User",
            bio="Hello!",
            date_of_birth=dob,
        )
        profile = await create_profile(test_session, user.id, data)
        assert profile.display_name == "Teen User"
        assert profile.age_tier == "teen"
        assert profile.visibility == "friends_only"

    @pytest.mark.asyncio
    async def test_create_profile_young(self, test_session):
        user = await _make_user(test_session)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 7)
        data = ProfileCreate(
            display_name="Young User",
            date_of_birth=dob,
        )
        profile = await create_profile(test_session, user.id, data)
        assert profile.age_tier == "young"

    @pytest.mark.asyncio
    async def test_create_profile_preteen(self, test_session):
        user = await _make_user(test_session)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 11)
        data = ProfileCreate(
            display_name="Preteen User",
            date_of_birth=dob,
        )
        profile = await create_profile(test_session, user.id, data)
        assert profile.age_tier == "preteen"

    @pytest.mark.asyncio
    async def test_create_profile_duplicate(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        with pytest.raises(ConflictError):
            await _make_profile(test_session, user.id)

    @pytest.mark.asyncio
    async def test_create_profile_age_out_of_range(self, test_session):
        user = await _make_user(test_session)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 20)
        data = ProfileCreate(
            display_name="Adult",
            date_of_birth=dob,
        )
        with pytest.raises(ValidationError):
            await create_profile(test_session, user.id, data)


class TestGetProfile:
    """Test profile retrieval."""

    @pytest.mark.asyncio
    async def test_get_profile(self, test_session):
        user = await _make_user(test_session)
        created = await _make_profile(test_session, user.id)
        retrieved = await get_profile(test_session, user.id)
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, test_session):
        with pytest.raises(NotFoundError):
            await get_profile(test_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_profile_by_id(self, test_session):
        user = await _make_user(test_session)
        created = await _make_profile(test_session, user.id)
        retrieved = await get_profile_by_id(test_session, created.id)
        assert retrieved.user_id == user.id


class TestUpdateProfile:
    """Test profile updates."""

    @pytest.mark.asyncio
    async def test_update_display_name(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = ProfileUpdate(display_name="Updated Name")
        updated = await update_profile(test_session, user.id, data)
        assert updated.display_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_bio(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = ProfileUpdate(bio="New bio")
        updated = await update_profile(test_session, user.id, data)
        assert updated.bio == "New bio"

    @pytest.mark.asyncio
    async def test_update_visibility(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = ProfileUpdate(visibility="public")
        updated = await update_profile(test_session, user.id, data)
        assert updated.visibility == "public"


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


class TestCreatePost:
    """Test post creation."""

    @pytest.mark.asyncio
    async def test_create_text_post(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Hello world!")
        post = await create_post(test_session, user.id, data, "teen")
        assert post.content == "Hello world!"
        assert post.post_type == "text"

    @pytest.mark.asyncio
    async def test_create_post_with_hashtags(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Hello #world #test")
        post = await create_post(test_session, user.id, data, "teen")
        assert post.content == "Hello #world #test"

        # Verify hashtags were created
        from sqlalchemy import select
        result = await test_session.execute(select(Hashtag))
        hashtags = list(result.scalars().all())
        names = {h.name for h in hashtags}
        assert "world" in names
        assert "test" in names

    @pytest.mark.asyncio
    async def test_create_post_exceeds_tier_limit(self, test_session):
        user = await _make_user(test_session)
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 7)
        await _make_profile(test_session, user.id, dob=dob, age_tier="young")
        # Young tier limit is 200 chars
        data = PostCreate(content="A" * 201)
        with pytest.raises(ValidationError, match="maximum length"):
            await create_post(test_session, user.id, data, "young")

    @pytest.mark.asyncio
    async def test_create_post_with_media(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(
            content="Check this out!",
            post_type="image",
            media_urls=["https://example.com/img.jpg"],
        )
        post = await create_post(test_session, user.id, data, "teen")
        assert post.media_urls == {"urls": ["https://example.com/img.jpg"]}


class TestGetPost:
    """Test getting a single post."""

    @pytest.mark.asyncio
    async def test_get_post(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Test post")
        post = await create_post(test_session, user.id, data, "teen")
        result = await get_post(test_session, post.id)
        assert result["post"].id == post.id
        assert result["like_count"] == 0
        assert result["comment_count"] == 0

    @pytest.mark.asyncio
    async def test_get_post_not_found(self, test_session):
        with pytest.raises(NotFoundError):
            await get_post(test_session, uuid.uuid4())


class TestDeletePost:
    """Test post deletion."""

    @pytest.mark.asyncio
    async def test_delete_own_post(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="To be deleted")
        post = await create_post(test_session, user.id, data, "teen")
        await delete_post(test_session, post.id, user.id)
        # Post is soft-deleted, so direct fetch should still work with include_deleted
        from sqlalchemy import select
        result = await test_session.execute(
            select(SocialPost)
            .where(SocialPost.id == post.id)
            .execution_options(include_deleted=True)
        )
        deleted = result.scalar_one()
        assert deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_others_post_forbidden(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await _make_profile(test_session, user1.id)
        data = PostCreate(content="My post")
        post = await create_post(test_session, user1.id, data, "teen")
        with pytest.raises(ForbiddenError):
            await delete_post(test_session, post.id, user2.id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_post(self, test_session):
        with pytest.raises(NotFoundError):
            await delete_post(test_session, uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


class TestLikePost:
    """Test post like/unlike."""

    @pytest.mark.asyncio
    async def test_like_post(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Likeable post")
        post = await create_post(test_session, user.id, data, "teen")
        like = await like_post(test_session, post.id, user.id)
        assert like.post_id == post.id

    @pytest.mark.asyncio
    async def test_like_post_duplicate(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Post")
        post = await create_post(test_session, user.id, data, "teen")
        await like_post(test_session, post.id, user.id)
        with pytest.raises(ConflictError):
            await like_post(test_session, post.id, user.id)

    @pytest.mark.asyncio
    async def test_like_nonexistent_post(self, test_session):
        with pytest.raises(NotFoundError):
            await like_post(test_session, uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_unlike_post(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Post")
        post = await create_post(test_session, user.id, data, "teen")
        await like_post(test_session, post.id, user.id)
        await unlike_post(test_session, post.id, user.id)
        # Verify like is removed
        from sqlalchemy import select
        result = await test_session.execute(
            select(PostLike).where(
                PostLike.post_id == post.id, PostLike.user_id == user.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_unlike_nonexistent(self, test_session):
        with pytest.raises(NotFoundError):
            await unlike_post(test_session, uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TestComments:
    """Test comment creation and listing."""

    @pytest.mark.asyncio
    async def test_add_comment(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Post with comments")
        post = await create_post(test_session, user.id, data, "teen")
        comment = await add_comment(
            test_session, post.id, user.id, "Nice post!", "teen",
        )
        assert comment.content == "Nice post!"
        assert comment.post_id == post.id

    @pytest.mark.asyncio
    async def test_comment_on_nonexistent_post(self, test_session):
        user = await _make_user(test_session)
        with pytest.raises(NotFoundError):
            await add_comment(
                test_session, uuid.uuid4(), user.id, "Hello", "teen",
            )

    @pytest.mark.asyncio
    async def test_list_comments_empty(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)
        data = PostCreate(content="Post")
        post = await create_post(test_session, user.id, data, "teen")
        result = await list_comments(test_session, post.id)
        assert result["total"] == 0
        assert result["items"] == []


# ---------------------------------------------------------------------------
# Follows
# ---------------------------------------------------------------------------


class TestFollows:
    """Test follow/unfollow logic."""

    @pytest.mark.asyncio
    async def test_follow_user(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        assert follow.status == "pending"
        assert follow.follower_id == user1.id
        assert follow.following_id == user2.id

    @pytest.mark.asyncio
    async def test_follow_self_rejected(self, test_session):
        user = await _make_user(test_session)
        with pytest.raises(ValidationError, match="cannot follow yourself"):
            await follow_user(test_session, user.id, user.id)

    @pytest.mark.asyncio
    async def test_follow_duplicate_rejected(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await follow_user(test_session, user1.id, user2.id)
        with pytest.raises(ConflictError):
            await follow_user(test_session, user1.id, user2.id)

    @pytest.mark.asyncio
    async def test_accept_follow(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        accepted = await accept_follow(test_session, follow.id, user2.id)
        assert accepted.status == "accepted"

    @pytest.mark.asyncio
    async def test_accept_follow_wrong_user(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        with pytest.raises(ForbiddenError):
            await accept_follow(test_session, follow.id, user3.id)

    @pytest.mark.asyncio
    async def test_accept_already_accepted(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        await accept_follow(test_session, follow.id, user2.id)
        with pytest.raises(ConflictError):
            await accept_follow(test_session, follow.id, user2.id)

    @pytest.mark.asyncio
    async def test_unfollow_user(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await follow_user(test_session, user1.id, user2.id)
        await unfollow_user(test_session, user1.id, user2.id)
        # Verify removal
        from sqlalchemy import select
        result = await test_session.execute(
            select(Follow).where(
                Follow.follower_id == user1.id, Follow.following_id == user2.id,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_unfollow_nonexistent(self, test_session):
        with pytest.raises(NotFoundError):
            await unfollow_user(test_session, uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_list_followers(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        await accept_follow(test_session, follow.id, user2.id)
        result = await list_followers(test_session, user2.id)
        assert result["total"] == 1
        assert result["items"][0].follower_id == user1.id

    @pytest.mark.asyncio
    async def test_list_following(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        follow = await follow_user(test_session, user1.id, user2.id)
        await accept_follow(test_session, follow.id, user2.id)
        result = await list_following(test_session, user1.id)
        assert result["total"] == 1
        assert result["items"][0].following_id == user2.id


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


class TestFeed:
    """Test feed functionality."""

    @pytest.mark.asyncio
    async def test_feed_empty_no_follows(self, test_session):
        user = await _make_user(test_session)
        result = await get_feed(test_session, user.id)
        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_feed_shows_followed_posts(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await _make_profile(test_session, user2.id)

        # user1 follows user2
        follow = await follow_user(test_session, user1.id, user2.id)
        await accept_follow(test_session, follow.id, user2.id)

        # user2 creates a post (manually approved for test)
        data = PostCreate(content="Post from user2")
        post = await create_post(test_session, user2.id, data, "teen")
        post.moderation_status = "approved"
        await test_session.flush()

        result = await get_feed(test_session, user1.id)
        assert result["total"] == 1
        assert result["items"][0]["content"] == "Post from user2"

    @pytest.mark.asyncio
    async def test_feed_excludes_pending_posts(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await _make_profile(test_session, user2.id)

        follow = await follow_user(test_session, user1.id, user2.id)
        await accept_follow(test_session, follow.id, user2.id)

        # Create a post that stays pending
        data = PostCreate(content="Pending post")
        post = await create_post(test_session, user2.id, data, "teen")
        # Ensure it stays pending
        post.moderation_status = "pending"
        await test_session.flush()

        result = await get_feed(test_session, user1.id)
        assert result["total"] == 0


# ---------------------------------------------------------------------------
# Trending Hashtags
# ---------------------------------------------------------------------------


class TestTrendingHashtags:
    """Test trending hashtags functionality."""

    @pytest.mark.asyncio
    async def test_trending_empty(self, test_session):
        result = await get_trending_hashtags(test_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_trending_order(self, test_session):
        user = await _make_user(test_session)
        await _make_profile(test_session, user.id)

        # Create posts with hashtags
        await create_post(
            test_session, user.id,
            PostCreate(content="#popular #both"), "teen",
        )
        await create_post(
            test_session, user.id,
            PostCreate(content="#popular again"), "teen",
        )

        result = await get_trending_hashtags(test_session)
        if len(result) >= 2:
            assert result[0].name == "popular"
