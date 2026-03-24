"""Pydantic v2 schemas for the creative module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Allowed value sets
# ---------------------------------------------------------------------------

ALLOWED_THEMES = {"adventure", "friendship", "mystery", "science", "fantasy", "humor"}
ALLOWED_TEMPLATE_TYPES = {"fill_in_blank", "free_write"}
ALLOWED_MODERATION_STATUSES = {"pending", "approved", "rejected"}
ALLOWED_CATEGORIES = {"branded", "seasonal", "educational", "user_created"}
ALLOWED_AGE_TIERS = {"young", "preteen", "teen"}


# ---------------------------------------------------------------------------
# ArtGeneration
# ---------------------------------------------------------------------------


class ArtGenerationCreate(BaseModel):
    """Schema for requesting AI art generation."""

    prompt: str = Field(..., min_length=1, max_length=500)
    model: str = Field(default="dalle3", max_length=30)


class ArtGenerationResponse(BaseModel):
    """Schema for AI art generation responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    prompt: str
    sanitized_prompt: str
    model: str
    image_url: str | None = None
    cost: float
    moderation_status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("moderation_status")
    @classmethod
    def validate_moderation_status(cls, v: str) -> str:
        if v not in ALLOWED_MODERATION_STATUSES:
            raise ValueError(f"moderation_status must be one of {ALLOWED_MODERATION_STATUSES}")
        return v


# ---------------------------------------------------------------------------
# StoryTemplate
# ---------------------------------------------------------------------------


class StoryTemplateCreate(BaseModel):
    """Schema for creating a story template (admin/internal use)."""

    title: str = Field(..., min_length=1, max_length=200)
    theme: str = Field(..., max_length=30)
    content_template: str = Field(..., min_length=1)
    min_age_tier: str = Field(..., max_length=20)
    template_type: str = Field(..., max_length=30)

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if v not in ALLOWED_THEMES:
            raise ValueError(f"theme must be one of {ALLOWED_THEMES}")
        return v

    @field_validator("min_age_tier")
    @classmethod
    def validate_min_age_tier(cls, v: str) -> str:
        if v not in ALLOWED_AGE_TIERS:
            raise ValueError(f"min_age_tier must be one of {ALLOWED_AGE_TIERS}")
        return v

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v: str) -> str:
        if v not in ALLOWED_TEMPLATE_TYPES:
            raise ValueError(f"template_type must be one of {ALLOWED_TEMPLATE_TYPES}")
        return v


class StoryTemplateResponse(BaseModel):
    """Schema for story template responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    theme: str
    content_template: str
    min_age_tier: str
    template_type: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# StoryCreation
# ---------------------------------------------------------------------------


class StoryCreationCreate(BaseModel):
    """Schema for creating a member story."""

    template_id: UUID | None = None
    content: str = Field(..., min_length=1)


class StoryCreationResponse(BaseModel):
    """Schema for story creation responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    template_id: UUID | None = None
    content: str
    moderation_status: str
    posted_to_feed: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# StickerPack
# ---------------------------------------------------------------------------


class StickerPackCreate(BaseModel):
    """Schema for creating a sticker pack."""

    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., max_length=30)
    is_curated: bool = False

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {ALLOWED_CATEGORIES}")
        return v


class StickerPackResponse(BaseModel):
    """Schema for sticker pack responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str
    is_curated: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Sticker
# ---------------------------------------------------------------------------


class StickerCreate(BaseModel):
    """Schema for creating a sticker."""

    pack_id: UUID
    image_url: str = Field(..., max_length=500)
    member_id: UUID | None = None  # null for curated stickers


class StickerResponse(BaseModel):
    """Schema for sticker responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pack_id: UUID
    member_id: UUID | None = None
    image_url: str
    moderation_status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DrawingAsset
# ---------------------------------------------------------------------------


class DrawingAssetCreate(BaseModel):
    """Schema for submitting a member drawing."""

    image_url: str = Field(..., max_length=500)


class DrawingAssetResponse(BaseModel):
    """Schema for drawing asset responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    image_url: str
    moderation_status: str
    posted_to_feed: bool
    created_at: datetime
    updated_at: datetime
