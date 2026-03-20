"""Pydantic v2 schemas for the media module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class UploadURLRequest(BaseModel):
    """Request a presigned upload URL."""

    media_type: str = Field(..., pattern=r"^(image|video)$")
    content_length: int | None = Field(default=None, ge=1)
    filename: str | None = Field(default=None, max_length=255)


class RegisterMediaRequest(BaseModel):
    """Register a media asset after upload completes."""

    cloudflare_id: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., pattern=r"^(image|video)$")
    r2_key: str | None = Field(default=None, max_length=1024)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class UploadURLResponse(BaseModel):
    """Presigned upload URL response."""

    upload_url: str
    media_id: UUID
    expires_at: datetime


class MediaAssetResponse(BaseModel):
    """Single media asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cloudflare_r2_key: str | None = None
    cloudflare_image_id: str | None = None
    cloudflare_stream_id: str | None = None
    media_type: str
    moderation_status: str
    owner_id: UUID
    variants: dict | None = None
    content_length: int | None = None
    created_at: datetime


class MediaListResponse(BaseModel):
    """Paginated media list response."""

    items: list[MediaAssetResponse]
    total: int
    page: int
    page_size: int
