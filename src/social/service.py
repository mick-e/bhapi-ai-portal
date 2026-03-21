"""Social module business logic — profiles, posts, comments, likes, follows, feed."""

import re
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import AgeTier, age_from_dob, check_permission, get_tier_for_age
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.social.models import (
    Follow,
    Hashtag,
    PostComment,
    PostHashtag,
    PostLike,
    Profile,
    SocialPost,
)
from src.social.schemas import PostCreate, ProfileCreate, ProfileUpdate

logger = structlog.get_logger()

_HASHTAG_RE = re.compile(r"#([a-zA-Z0-9_]+)")


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


async def create_profile(
    db: AsyncSession, user_id: UUID, data: ProfileCreate,
) -> Profile:
    """Create a social profile for a user."""

    # Check if profile already exists
    existing = await db.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Profile already exists for this user")

    age = age_from_dob(data.date_of_birth)
    tier = get_tier_for_age(age)
    if tier is None:
        raise ValidationError(
            "Age must be between 5 and 15 to create a social profile"
        )

    profile = Profile(
        id=uuid4(),
        user_id=user_id,
        display_name=data.display_name,
        bio=data.bio,
        avatar_url=data.avatar_url,
        date_of_birth=data.date_of_birth,
        age_tier=tier.value,
        visibility=data.visibility,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    logger.info("profile_created", user_id=str(user_id), age_tier=tier.value)
    return profile


async def get_profile(db: AsyncSession, user_id: UUID) -> Profile:
    """Get profile by user_id."""
    result = await db.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError("Profile")
    return profile


async def get_profile_by_id(db: AsyncSession, profile_id: UUID) -> Profile:
    """Get profile by profile id."""
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError("Profile", str(profile_id))
    return profile


async def update_profile(
    db: AsyncSession, user_id: UUID, data: ProfileUpdate,
) -> Profile:
    """Partial update of a user's profile."""
    profile = await get_profile(db, user_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)

    logger.info("profile_updated", user_id=str(user_id))
    return profile


# ---------------------------------------------------------------------------
# Hashtags
# ---------------------------------------------------------------------------


def extract_hashtags(content: str) -> list[str]:
    """Extract hashtags from content using regex."""
    return _HASHTAG_RE.findall(content)


async def _ensure_hashtags(
    db: AsyncSession, post_id: UUID, tags: list[str],
) -> None:
    """Create or update hashtags and link them to a post."""
    for tag_name in tags:
        tag_lower = tag_name.lower()
        result = await db.execute(
            select(Hashtag).where(Hashtag.name == tag_lower)
        )
        hashtag = result.scalar_one_or_none()
        if hashtag:
            hashtag.post_count += 1
        else:
            hashtag = Hashtag(id=uuid4(), name=tag_lower, post_count=1)
            db.add(hashtag)
            await db.flush()

        link = PostHashtag(id=uuid4(), post_id=post_id, hashtag_id=hashtag.id)
        db.add(link)

    await db.flush()


async def get_trending_hashtags(
    db: AsyncSession, limit: int = 10,
) -> list[Hashtag]:
    """Get top hashtags by post_count."""
    result = await db.execute(
        select(Hashtag)
        .where(Hashtag.post_count > 0)
        .order_by(Hashtag.post_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


async def create_post(
    db: AsyncSession,
    author_id: UUID,
    data: PostCreate,
    age_tier: str,
) -> SocialPost:
    """Create a social post with moderation and hashtag extraction."""
    from src.moderation import submit_for_moderation

    tier = AgeTier(age_tier)

    if not check_permission(tier, "can_post"):
        raise ForbiddenError("You do not have permission to create posts")

    # Enforce max post length per tier
    from src.age_tier.rules import TIER_PERMISSIONS
    max_len = TIER_PERMISSIONS[tier]["max_post_length"]
    if len(data.content) > max_len:
        raise ValidationError(
            f"Post content exceeds maximum length of {max_len} characters for your age tier"
        )

    media_dict = {"urls": data.media_urls} if data.media_urls else None

    post = SocialPost(
        id=uuid4(),
        author_id=author_id,
        content=data.content,
        post_type=data.post_type,
        media_urls=media_dict,
        moderation_status="pending",
    )
    db.add(post)
    await db.flush()

    # Submit to moderation pipeline
    mod_entry = await submit_for_moderation(
        db,
        content_type="post",
        content_id=post.id,
        author_age_tier=age_tier,
        content_text=data.content,
    )
    # Update post moderation status based on moderation result
    post.moderation_status = mod_entry.status
    await db.flush()

    # Extract and store hashtags
    tags = extract_hashtags(data.content)
    if tags:
        await _ensure_hashtags(db, post.id, tags)

    await db.refresh(post)

    logger.info(
        "post_created",
        post_id=str(post.id),
        author_id=str(author_id),
        moderation_status=post.moderation_status,
    )
    return post


async def get_post(db: AsyncSession, post_id: UUID) -> dict:
    """Get a single post with like and comment counts."""
    result = await db.execute(
        select(SocialPost).where(SocialPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundError("Post", str(post_id))

    like_count = (
        await db.execute(
            select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
        )
    ).scalar() or 0

    comment_count = (
        await db.execute(
            select(func.count(PostComment.id)).where(
                PostComment.post_id == post_id,
                PostComment.deleted_at.is_(None),
            )
        )
    ).scalar() or 0

    return {
        "post": post,
        "like_count": like_count,
        "comment_count": comment_count,
    }


async def list_posts(
    db: AsyncSession,
    author_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List posts, optionally filtered by author. Only approved posts in public listing."""
    base = select(SocialPost).where(SocialPost.moderation_status == "approved")
    count_q = select(func.count(SocialPost.id)).where(
        SocialPost.moderation_status == "approved"
    )

    if author_id:
        base = base.where(SocialPost.author_id == author_id)
        count_q = count_q.where(SocialPost.author_id == author_id)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(SocialPost.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    posts = list(rows.scalars().all())

    # Attach counts to each post
    items = []
    for p in posts:
        like_count = (
            await db.execute(
                select(func.count(PostLike.id)).where(PostLike.post_id == p.id)
            )
        ).scalar() or 0
        comment_count = (
            await db.execute(
                select(func.count(PostComment.id)).where(
                    PostComment.post_id == p.id,
                    PostComment.deleted_at.is_(None),
                )
            )
        ).scalar() or 0
        items.append({
            "id": p.id,
            "author_id": p.author_id,
            "content": p.content,
            "post_type": p.post_type,
            "media_urls": p.media_urls,
            "moderation_status": p.moderation_status,
            "like_count": like_count,
            "comment_count": comment_count,
            "created_at": p.created_at,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def delete_post(
    db: AsyncSession, post_id: UUID, user_id: UUID,
) -> None:
    """Soft-delete a post (author only)."""
    result = await db.execute(
        select(SocialPost).where(SocialPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise NotFoundError("Post", str(post_id))
    if post.author_id != user_id:
        raise ForbiddenError("You can only delete your own posts")

    post.soft_delete()
    await db.flush()

    logger.info("post_deleted", post_id=str(post_id), user_id=str(user_id))


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


async def like_post(db: AsyncSession, post_id: UUID, user_id: UUID) -> PostLike:
    """Like a post. Raises ConflictError if already liked."""
    # Verify post exists
    result = await db.execute(
        select(SocialPost).where(SocialPost.id == post_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Post", str(post_id))

    # Check duplicate
    existing = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id, PostLike.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You have already liked this post")

    like = PostLike(id=uuid4(), post_id=post_id, user_id=user_id)
    db.add(like)
    await db.flush()
    await db.refresh(like)
    return like


async def unlike_post(db: AsyncSession, post_id: UUID, user_id: UUID) -> None:
    """Remove a like from a post."""
    result = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id, PostLike.user_id == user_id,
        )
    )
    like = result.scalar_one_or_none()
    if not like:
        raise NotFoundError("Like")
    await db.delete(like)
    await db.flush()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


async def add_comment(
    db: AsyncSession,
    post_id: UUID,
    author_id: UUID,
    content: str,
    age_tier: str,
) -> PostComment:
    """Add a comment to a post, submit for moderation."""
    from src.moderation import submit_for_moderation

    tier = AgeTier(age_tier)

    if not check_permission(tier, "can_comment"):
        raise ForbiddenError("You do not have permission to comment")

    # Verify post exists
    result = await db.execute(
        select(SocialPost).where(SocialPost.id == post_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Post", str(post_id))

    comment = PostComment(
        id=uuid4(),
        post_id=post_id,
        author_id=author_id,
        content=content,
        moderation_status="pending",
    )
    db.add(comment)
    await db.flush()

    mod_entry = await submit_for_moderation(
        db,
        content_type="comment",
        content_id=comment.id,
        author_age_tier=age_tier,
        content_text=content,
    )
    comment.moderation_status = mod_entry.status
    await db.flush()
    await db.refresh(comment)

    logger.info(
        "comment_created",
        comment_id=str(comment.id),
        post_id=str(post_id),
        moderation_status=comment.moderation_status,
    )
    return comment


async def list_comments(
    db: AsyncSession, post_id: UUID, page: int = 1, page_size: int = 20,
) -> dict:
    """List comments on a post (only approved ones)."""
    base = select(PostComment).where(
        PostComment.post_id == post_id,
        PostComment.moderation_status == "approved",
    )
    count_q = select(func.count(PostComment.id)).where(
        PostComment.post_id == post_id,
        PostComment.moderation_status == "approved",
    )

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(PostComment.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows.scalars().all())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


async def get_feed(
    db: AsyncSession, user_id: UUID, page: int = 1, page_size: int = 20,
) -> dict:
    """Get personalized feed — approved posts from followed users, chronological."""
    # Get IDs of users this user follows (accepted only)
    following_q = select(Follow.following_id).where(
        Follow.follower_id == user_id,
        Follow.status == "accepted",
    )
    following_result = await db.execute(following_q)
    following_ids = [row[0] for row in following_result.all()]

    if not following_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    base = select(SocialPost).where(
        SocialPost.author_id.in_(following_ids),
        SocialPost.moderation_status == "approved",
    )
    count_q = select(func.count(SocialPost.id)).where(
        SocialPost.author_id.in_(following_ids),
        SocialPost.moderation_status == "approved",
    )

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(SocialPost.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    posts = list(rows.scalars().all())

    items = []
    for p in posts:
        like_count = (
            await db.execute(
                select(func.count(PostLike.id)).where(PostLike.post_id == p.id)
            )
        ).scalar() or 0
        comment_count = (
            await db.execute(
                select(func.count(PostComment.id)).where(
                    PostComment.post_id == p.id,
                    PostComment.deleted_at.is_(None),
                )
            )
        ).scalar() or 0
        items.append({
            "id": p.id,
            "author_id": p.author_id,
            "content": p.content,
            "post_type": p.post_type,
            "media_urls": p.media_urls,
            "moderation_status": p.moderation_status,
            "like_count": like_count,
            "comment_count": comment_count,
            "created_at": p.created_at,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ---------------------------------------------------------------------------
# Follows
# ---------------------------------------------------------------------------


async def follow_user(
    db: AsyncSession, follower_id: UUID, following_id: UUID,
) -> Follow:
    """Create a follow request."""
    if follower_id == following_id:
        raise ValidationError("You cannot follow yourself")

    # Check for existing follow
    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You are already following or have a pending request for this user")

    follow = Follow(
        id=uuid4(),
        follower_id=follower_id,
        following_id=following_id,
        status="pending",
    )
    db.add(follow)
    await db.flush()
    await db.refresh(follow)

    logger.info(
        "follow_requested",
        follower_id=str(follower_id),
        following_id=str(following_id),
    )
    return follow


async def unfollow_user(
    db: AsyncSession, follower_id: UUID, following_id: UUID,
) -> None:
    """Remove a follow relationship."""
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id,
        )
    )
    follow = result.scalar_one_or_none()
    if not follow:
        raise NotFoundError("Follow relationship")

    await db.delete(follow)
    await db.flush()

    logger.info(
        "unfollowed",
        follower_id=str(follower_id),
        following_id=str(following_id),
    )


async def accept_follow(
    db: AsyncSession, follow_id: UUID, user_id: UUID,
) -> Follow:
    """Accept a pending follow request (only the followed user can accept)."""
    result = await db.execute(
        select(Follow).where(Follow.id == follow_id)
    )
    follow = result.scalar_one_or_none()
    if not follow:
        raise NotFoundError("Follow request", str(follow_id))

    if follow.following_id != user_id:
        raise ForbiddenError("You can only accept follow requests directed to you")

    if follow.status != "pending":
        raise ConflictError(f"Follow request is already {follow.status}")

    follow.status = "accepted"
    await db.flush()
    await db.refresh(follow)

    logger.info(
        "follow_accepted",
        follow_id=str(follow_id),
        follower_id=str(follow.follower_id),
        following_id=str(follow.following_id),
    )
    return follow


async def list_followers(
    db: AsyncSession, user_id: UUID, page: int = 1, page_size: int = 20,
) -> dict:
    """List accepted followers of a user."""
    base = select(Follow).where(
        Follow.following_id == user_id,
        Follow.status == "accepted",
    )
    count_q = select(func.count(Follow.id)).where(
        Follow.following_id == user_id,
        Follow.status == "accepted",
    )

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(Follow.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows.scalars().all())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def list_following(
    db: AsyncSession, user_id: UUID, page: int = 1, page_size: int = 20,
) -> dict:
    """List users that a given user is following (accepted only)."""
    base = select(Follow).where(
        Follow.follower_id == user_id,
        Follow.status == "accepted",
    )
    count_q = select(func.count(Follow.id)).where(
        Follow.follower_id == user_id,
        Follow.status == "accepted",
    )

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(Follow.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows.scalars().all())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ---------------------------------------------------------------------------
# Profile Search
# ---------------------------------------------------------------------------


async def search_profiles(
    db: AsyncSession,
    query: str,
    requester_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Search profiles by display_name (case-insensitive).

    Excludes:
    - The requester's own profile.
    - Profiles of users who have blocked the requester (or vice versa).
    - Private profiles (visibility == "private").

    Results are paginated.
    """
    from sqlalchemy import or_

    from src.contacts.models import Contact

    if not query or not query.strip():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    search_term = f"%{query.strip().lower()}%"

    # Find blocked user IDs (both directions)
    blocked_q = select(Contact).where(
        or_(
            Contact.requester_id == requester_id,
            Contact.target_id == requester_id,
        ),
        Contact.status == "blocked",
    )
    blocked_result = await db.execute(blocked_q)
    blocked_contacts = list(blocked_result.scalars().all())

    blocked_ids = set()
    for c in blocked_contacts:
        if c.requester_id == requester_id:
            blocked_ids.add(c.target_id)
        else:
            blocked_ids.add(c.requester_id)

    # Build search query
    base_filters = [
        func.lower(Profile.display_name).like(search_term),
        Profile.user_id != requester_id,
        Profile.visibility != "private",
    ]

    if blocked_ids:
        base_filters.append(Profile.user_id.notin_(blocked_ids))

    count_result = await db.execute(
        select(func.count()).select_from(Profile).where(*base_filters)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Profile)
        .where(*base_filters)
        .order_by(Profile.display_name)
        .offset(offset)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    logger.info(
        "profile_search",
        requester_id=str(requester_id),
        query=query,
        results=len(items),
        total=total,
    )

    return {"items": items, "total": total, "page": page, "page_size": page_size}
