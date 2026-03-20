"""Social feature database models."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Profile(Base, UUIDMixin, TimestampMixin):
    """User social profile."""

    __tablename__ = "profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_profiles_user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="friends_only",
    )


class SocialPost(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User-created social post."""

    __tablename__ = "social_posts"

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    post_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text",
    )  # text, image, video, mixed
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected, removed


class PostComment(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Comment on a social post."""

    __tablename__ = "post_comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected, removed


class PostLike(Base, UUIDMixin, TimestampMixin):
    """Like on a social post."""

    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )


class Hashtag(Base, UUIDMixin, TimestampMixin):
    """Hashtag for categorising posts."""

    __tablename__ = "hashtags"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PostHashtag(Base, UUIDMixin, TimestampMixin):
    """Association between posts and hashtags."""

    __tablename__ = "post_hashtags"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    hashtag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hashtags.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )


class Follow(Base, UUIDMixin, TimestampMixin):
    """Follow relationship between users."""

    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint(
            "follower_id", "following_id", name="uq_follows_follower_following",
        ),
    )

    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, accepted, blocked
