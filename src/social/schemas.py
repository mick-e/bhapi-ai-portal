"""Pydantic v2 schemas for the social module."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


class ProfileCreate(BaseModel):
    """Schema for creating a social profile."""

    display_name: str = Field(..., min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=1024)
    date_of_birth: date
    visibility: str = Field(default="friends_only", pattern=r"^(public|friends_only|private)$")


class ProfileUpdate(BaseModel):
    """Schema for updating a social profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=1024)
    visibility: str | None = Field(default=None, pattern=r"^(public|friends_only|private)$")


class ProfileResponse(BaseModel):
    """Schema for profile responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    age_tier: str
    visibility: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


class PostCreate(BaseModel):
    """Schema for creating a social post."""

    content: str = Field(..., min_length=1, max_length=1000)
    post_type: str = Field(default="text", pattern=r"^(text|image|video|mixed)$")
    media_urls: list[str] | None = None


class PostResponse(BaseModel):
    """Schema for post responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    content: str
    post_type: str
    media_urls: dict | None = None
    moderation_status: str
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime


class PostListResponse(BaseModel):
    """Paginated list of posts."""

    items: list[PostResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    content: str = Field(..., min_length=1, max_length=500)


class CommentResponse(BaseModel):
    """Schema for comment responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    author_id: UUID
    content: str
    moderation_status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Follows
# ---------------------------------------------------------------------------


class FollowResponse(BaseModel):
    """Schema for follow relationship responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    follower_id: UUID
    following_id: UUID
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


class FeedResponse(BaseModel):
    """Paginated feed response."""

    items: list[PostResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Hashtags
# ---------------------------------------------------------------------------


class HashtagResponse(BaseModel):
    """Schema for hashtag responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    post_count: int
