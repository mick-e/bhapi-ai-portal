"""Creative feature database models — AI art, stories, stickers, drawings."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class ArtGeneration(Base, UUIDMixin, TimestampMixin):
    """AI-generated artwork created by a member using a text prompt."""

    __tablename__ = "art_generations"
    __table_args__ = (
        Index("ix_art_generations_member_moderation", "member_id", "moderation_status"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(30), nullable=False, default="dalle3")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected


class StoryTemplate(Base, UUIDMixin, TimestampMixin):
    """Pre-built story template that members can use for guided writing."""

    __tablename__ = "story_templates"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    theme: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # adventure, friendship, mystery, science, fantasy, humor
    content_template: Mapped[str] = mapped_column(Text, nullable=False)
    min_age_tier: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # young, preteen, teen
    template_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # fill_in_blank, free_write


class StoryCreation(Base, UUIDMixin, TimestampMixin):
    """A story written by a member, optionally using a template."""

    __tablename__ = "story_creations"
    __table_args__ = (
        Index("ix_story_creations_member_moderation", "member_id", "moderation_status"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("story_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected
    posted_to_feed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StickerPack(Base, UUIDMixin, TimestampMixin):
    """A collection of stickers grouped by category."""

    __tablename__ = "sticker_packs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # branded, seasonal, educational, user_created
    is_curated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Sticker(Base, UUIDMixin, TimestampMixin):
    """An individual sticker within a pack."""

    __tablename__ = "stickers"

    pack_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sticker_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # null for curated stickers
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected


class DrawingAsset(Base, UUIDMixin, TimestampMixin):
    """A freehand drawing created by a member."""

    __tablename__ = "drawing_assets"
    __table_args__ = (
        Index("ix_drawing_assets_member_moderation", "member_id", "moderation_status"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, approved, rejected
    posted_to_feed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
