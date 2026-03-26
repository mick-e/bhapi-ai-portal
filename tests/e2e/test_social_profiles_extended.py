"""E2E tests for social profile CRUD, followers, post history, visibility."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.social import service
from src.social.models import Profile, SocialPost
from src.social.schemas import ProfileCreate, ProfileUpdate
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_profile(
    session: AsyncSession,
    *,
    display_name: str = "Test User",
    bio: str | None = None,
    avatar_url: str | None = None,
    visibility: str = "friends_only",
    dob: date | None = None,
) -> tuple[Profile, uuid.UUID]:
    """Create a user + profile and return (profile, user_id)."""
    _, owner_id = await make_test_group(session)
    data = ProfileCreate(
        display_name=display_name,
        bio=bio,
        avatar_url=avatar_url,
        visibility=visibility,
        date_of_birth=dob or date(2014, 6, 15),  # age 11 → preteen
    )
    profile = await service.create_profile(session, owner_id, data)
    await session.commit()
    return profile, owner_id


async def _create_post(
    session: AsyncSession,
    author_id: uuid.UUID,
    content: str = "Hello world",
    moderation_status: str = "approved",
) -> SocialPost:
    """Directly create a post (bypasses moderation for speed)."""
    post = SocialPost(
        id=uuid.uuid4(),
        author_id=author_id,
        content=content,
        post_type="text",
        moderation_status=moderation_status,
    )
    session.add(post)
    await session.flush()
    return post


# ═══════════════════════════════════════════════════════════════════
# Profile CRUD
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_profile_update_display_name(test_session: AsyncSession):
    """Profile display_name can be updated."""
    profile, uid = await _create_profile(test_session, display_name="OldName")
    updated = await service.update_profile(
        test_session, uid, ProfileUpdate(display_name="NewName"),
    )
    await test_session.commit()
    assert updated.display_name == "NewName"


@pytest.mark.asyncio
async def test_profile_update_bio(test_session: AsyncSession):
    """Bio field can be set and cleared."""
    profile, uid = await _create_profile(test_session, bio=None)
    updated = await service.update_profile(
        test_session, uid, ProfileUpdate(bio="Hello world"),
    )
    await test_session.commit()
    assert updated.bio == "Hello world"


@pytest.mark.asyncio
async def test_profile_update_avatar_url(test_session: AsyncSession):
    """Avatar URL can be set."""
    profile, uid = await _create_profile(test_session)
    updated = await service.update_profile(
        test_session,
        uid,
        ProfileUpdate(avatar_url="https://cdn.bhapi.ai/avatars/abc.jpg"),
    )
    await test_session.commit()
    assert updated.avatar_url == "https://cdn.bhapi.ai/avatars/abc.jpg"


@pytest.mark.asyncio
async def test_profile_visibility_friends_only(test_session: AsyncSession):
    """Default visibility is friends_only."""
    profile, _ = await _create_profile(test_session)
    assert profile.visibility == "friends_only"


@pytest.mark.asyncio
async def test_profile_visibility_update_public(test_session: AsyncSession):
    """Visibility can be changed to public."""
    profile, uid = await _create_profile(test_session)
    updated = await service.update_profile(
        test_session, uid, ProfileUpdate(visibility="public"),
    )
    await test_session.commit()
    assert updated.visibility == "public"


@pytest.mark.asyncio
async def test_profile_visibility_update_private(test_session: AsyncSession):
    """Visibility can be changed to private."""
    profile, uid = await _create_profile(test_session)
    updated = await service.update_profile(
        test_session, uid, ProfileUpdate(visibility="private"),
    )
    await test_session.commit()
    assert updated.visibility == "private"


@pytest.mark.asyncio
async def test_profile_get_own(test_session: AsyncSession):
    """Can retrieve own profile by user_id."""
    profile, uid = await _create_profile(
        test_session, display_name="Alice", bio="Hi there",
    )
    fetched = await service.get_profile(test_session, uid)
    assert fetched.id == profile.id
    assert fetched.display_name == "Alice"
    assert fetched.bio == "Hi there"


@pytest.mark.asyncio
async def test_profile_get_another_user(test_session: AsyncSession):
    """Can retrieve another user's profile."""
    profile_a, uid_a = await _create_profile(
        test_session, display_name="UserA",
    )
    profile_b, uid_b = await _create_profile(
        test_session, display_name="UserB",
    )
    fetched = await service.get_profile(test_session, uid_b)
    assert fetched.display_name == "UserB"


@pytest.mark.asyncio
async def test_profile_not_found(test_session: AsyncSession):
    """NotFoundError for non-existent profile."""
    from src.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await service.get_profile(test_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_profile_duplicate_rejected(test_session: AsyncSession):
    """Cannot create two profiles for the same user."""
    from src.exceptions import ConflictError

    _, uid = await _create_profile(test_session)
    with pytest.raises(ConflictError):
        await service.create_profile(
            test_session,
            uid,
            ProfileCreate(
                display_name="Dup",
                date_of_birth=date(2014, 1, 1),
            ),
        )


# ═══════════════════════════════════════════════════════════════════
# Follower / Following List Pagination
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_follower_list_empty(test_session: AsyncSession):
    """Follower list is empty for a new profile."""
    _, uid = await _create_profile(test_session)
    result = await service.list_followers(test_session, uid)
    assert result["items"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_follower_list_accepted_only(test_session: AsyncSession):
    """Only accepted followers appear in the list."""
    _, uid_a = await _create_profile(test_session, display_name="A")
    _, uid_b = await _create_profile(test_session, display_name="B")

    follow = await service.follow_user(test_session, uid_b, uid_a)
    await test_session.commit()

    # Before acceptance — should be empty
    result = await service.list_followers(test_session, uid_a)
    assert result["total"] == 0

    # Accept
    await service.accept_follow(test_session, follow.id, uid_a)
    await test_session.commit()

    result = await service.list_followers(test_session, uid_a)
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_following_list_pagination(test_session: AsyncSession):
    """Following list supports pagination."""
    _, uid_main = await _create_profile(test_session, display_name="Main")

    # Create 3 users and follow them all
    follow_ids = []
    for i in range(3):
        _, uid_other = await _create_profile(
            test_session, display_name=f"Other{i}",
        )
        follow = await service.follow_user(test_session, uid_main, uid_other)
        await test_session.commit()
        await service.accept_follow(test_session, follow.id, uid_other)
        await test_session.commit()
        follow_ids.append(follow.id)

    # Page 1, size 2
    result = await service.list_following(test_session, uid_main, page=1, page_size=2)
    assert len(result["items"]) == 2
    assert result["total"] == 3

    # Page 2, size 2
    result2 = await service.list_following(test_session, uid_main, page=2, page_size=2)
    assert len(result2["items"]) == 1


@pytest.mark.asyncio
async def test_follower_list_pagination(test_session: AsyncSession):
    """Follower list supports pagination."""
    _, uid_target = await _create_profile(test_session, display_name="Target")

    for i in range(3):
        _, uid_follower = await _create_profile(
            test_session, display_name=f"Follower{i}",
        )
        follow = await service.follow_user(test_session, uid_follower, uid_target)
        await test_session.commit()
        await service.accept_follow(test_session, follow.id, uid_target)
        await test_session.commit()

    result = await service.list_followers(test_session, uid_target, page=1, page_size=2)
    assert len(result["items"]) == 2
    assert result["total"] == 3


# ═══════════════════════════════════════════════════════════════════
# Post History
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_post_history_for_user(test_session: AsyncSession):
    """Can list posts by a specific author."""
    _, uid = await _create_profile(test_session)
    await _create_post(test_session, uid, "Post 1")
    await _create_post(test_session, uid, "Post 2")
    await test_session.commit()

    result = await service.list_posts(test_session, author_id=uid, page=1, page_size=20)
    assert result["total"] == 2
    contents = [p["content"] for p in result["items"]]
    assert "Post 1" in contents
    assert "Post 2" in contents


@pytest.mark.asyncio
async def test_post_history_excludes_other_authors(test_session: AsyncSession):
    """Post history filtered by author_id excludes other users' posts."""
    _, uid_a = await _create_profile(test_session, display_name="A")
    _, uid_b = await _create_profile(test_session, display_name="B")

    await _create_post(test_session, uid_a, "A's post")
    await _create_post(test_session, uid_b, "B's post")
    await test_session.commit()

    result = await service.list_posts(test_session, author_id=uid_a, page=1, page_size=20)
    assert result["total"] == 1
    assert result["items"][0]["content"] == "A's post"


@pytest.mark.asyncio
async def test_post_history_pagination(test_session: AsyncSession):
    """Post history supports pagination."""
    _, uid = await _create_profile(test_session)
    for i in range(5):
        await _create_post(test_session, uid, f"Post {i}")
    await test_session.commit()

    page1 = await service.list_posts(test_session, author_id=uid, page=1, page_size=2)
    assert len(page1["items"]) == 2
    assert page1["total"] == 5

    page3 = await service.list_posts(test_session, author_id=uid, page=3, page_size=2)
    assert len(page3["items"]) == 1


@pytest.mark.asyncio
async def test_post_history_pending_excluded(test_session: AsyncSession):
    """Posts with non-approved moderation status are excluded from list."""
    _, uid = await _create_profile(test_session)
    await _create_post(test_session, uid, "Approved", moderation_status="approved")
    await _create_post(test_session, uid, "Pending", moderation_status="pending")
    await test_session.commit()

    result = await service.list_posts(test_session, author_id=uid, page=1, page_size=20)
    assert result["total"] == 1
    assert result["items"][0]["content"] == "Approved"


# ═══════════════════════════════════════════════════════════════════
# Visibility Settings Validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_visibility_valid_values(test_session: AsyncSession):
    """All three visibility values are accepted."""
    for vis in ("public", "friends_only", "private"):
        profile, _ = await _create_profile(test_session, visibility=vis)
        assert profile.visibility == vis


@pytest.mark.asyncio
async def test_visibility_invalid_rejected():
    """Invalid visibility value is rejected by schema validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfileCreate(
            display_name="Test",
            date_of_birth=date(2014, 1, 1),
            visibility="everyone",
        )


@pytest.mark.asyncio
async def test_profile_update_partial(test_session: AsyncSession):
    """Partial update only changes provided fields."""
    profile, uid = await _create_profile(
        test_session,
        display_name="Original",
        bio="Original bio",
        visibility="friends_only",
    )
    updated = await service.update_profile(
        test_session, uid, ProfileUpdate(bio="New bio"),
    )
    await test_session.commit()

    assert updated.display_name == "Original"
    assert updated.bio == "New bio"
    assert updated.visibility == "friends_only"
