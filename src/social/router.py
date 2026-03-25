"""Social module FastAPI router — profiles, posts, comments, likes, follows, feed."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.middleware import enforce_age_tier
from src.auth.middleware import get_current_user
from src.database import get_db
from src.schemas import GroupContext
from src.social import schemas, service

logger = structlog.get_logger()

router = APIRouter(dependencies=[Depends(enforce_age_tier)])


# ---------------------------------------------------------------------------
# Helper — resolve the user's age tier from their profile
# ---------------------------------------------------------------------------


async def _get_user_age_tier(db: AsyncSession, user_id: UUID) -> str:
    """Get the age tier for the authenticated user from their profile."""
    profile = await service.get_profile(db, user_id)
    return profile.age_tier


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


@router.post("/profiles", response_model=schemas.ProfileResponse, status_code=201)
async def create_profile(
    data: schemas.ProfileCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a social profile for the authenticated user."""
    profile = await service.create_profile(db, auth.user_id, data)
    await db.commit()
    return profile


@router.get("/profiles/me", response_model=schemas.ProfileResponse)
async def get_my_profile(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's profile."""
    return await service.get_profile(db, auth.user_id)


@router.put("/profiles/me", response_model=schemas.ProfileResponse)
async def update_my_profile(
    data: schemas.ProfileUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile."""
    profile = await service.update_profile(db, auth.user_id, data)
    await db.commit()
    return profile


@router.get("/profiles/{user_id}", response_model=schemas.ProfileResponse)
async def get_user_profile(
    user_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get another user's profile."""
    return await service.get_profile(db, user_id)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/search", response_model=schemas.SearchProfilesResponse)
async def search_users(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search users by display name (case-insensitive).

    Excludes blocked users, respects visibility settings, paginated.
    """
    return await service.search_profiles(
        db, query=q, requester_id=auth.user_id, page=page, page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


@router.post("/posts", response_model=schemas.PostResponse, status_code=201)
async def create_post(
    data: schemas.PostCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new post."""
    age_tier = await _get_user_age_tier(db, auth.user_id)
    post = await service.create_post(db, auth.user_id, data, age_tier)
    await db.commit()
    return schemas.PostResponse(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        post_type=post.post_type,
        media_urls=post.media_urls,
        moderation_status=post.moderation_status,
        like_count=0,
        comment_count=0,
        created_at=post.created_at,
    )


@router.get("/posts", response_model=schemas.PostListResponse)
async def list_posts(
    author_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List approved posts, optionally filtered by author."""
    return await service.list_posts(db, author_id=author_id, page=page, page_size=page_size)


@router.get("/posts/{post_id}", response_model=schemas.PostResponse)
async def get_post(
    post_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single post with like and comment counts."""
    result = await service.get_post(db, post_id)
    post = result["post"]
    return schemas.PostResponse(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        post_type=post.post_type,
        media_urls=post.media_urls,
        moderation_status=post.moderation_status,
        like_count=result["like_count"],
        comment_count=result["comment_count"],
        created_at=post.created_at,
    )


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a post (author only)."""
    await service.delete_post(db, post_id, auth.user_id)
    await db.commit()


@router.post("/posts/{post_id}/like", status_code=201)
async def like_post(
    post_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Like a post."""
    like = await service.like_post(db, post_id, auth.user_id)
    await db.commit()
    return {"id": str(like.id), "post_id": str(post_id), "user_id": str(auth.user_id)}


@router.delete("/posts/{post_id}/like", status_code=204)
async def unlike_post(
    post_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a like from a post."""
    await service.unlike_post(db, post_id, auth.user_id)
    await db.commit()


@router.post("/posts/{post_id}/comments", response_model=schemas.CommentResponse, status_code=201)
async def add_comment(
    post_id: UUID,
    data: schemas.CommentCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a post."""
    age_tier = await _get_user_age_tier(db, auth.user_id)
    comment = await service.add_comment(db, post_id, auth.user_id, data.content, age_tier)
    await db.commit()
    return comment


@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List approved comments on a post."""
    return await service.list_comments(db, post_id, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


@router.get("/feed", response_model=schemas.FeedResponse)
async def get_feed(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    algorithm: str = Query(
        default="chronological",
        pattern="^(chronological|engagement)$",
        description="Feed ordering algorithm: 'chronological' (newest first) or 'engagement' (likes + comments + recency).",
    ),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized feed from followed users.

    Use `algorithm=engagement` to rank posts by likes, comments, and recency decay
    instead of strict reverse-chronological order.
    """
    if algorithm == "engagement":
        return await service.get_feed_engagement(db, auth.user_id, page=page, page_size=page_size)
    return await service.get_feed(db, auth.user_id, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Follows
# ---------------------------------------------------------------------------


@router.post("/follow/{user_id}", response_model=schemas.FollowResponse, status_code=201)
async def follow_user(
    user_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a follow request to a user."""
    follow = await service.follow_user(db, auth.user_id, user_id)
    await db.commit()
    return follow


@router.delete("/follow/{user_id}", status_code=204)
async def unfollow_user(
    user_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unfollow a user."""
    await service.unfollow_user(db, auth.user_id, user_id)
    await db.commit()


@router.patch("/follow/{follow_id}/accept", response_model=schemas.FollowResponse)
async def accept_follow(
    follow_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pending follow request."""
    follow = await service.accept_follow(db, follow_id, auth.user_id)
    await db.commit()
    return follow


@router.get("/followers")
async def list_followers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List accepted followers."""
    return await service.list_followers(db, auth.user_id, page=page, page_size=page_size)


@router.get("/following")
async def list_following(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List who I follow."""
    return await service.list_following(db, auth.user_id, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Hashtags
# ---------------------------------------------------------------------------


@router.get("/hashtags/trending", response_model=list[schemas.HashtagResponse])
async def get_trending_hashtags(
    limit: int = Query(default=10, ge=1, le=50),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trending hashtags."""
    return await service.get_trending_hashtags(db, limit=limit)
