"""Contacts module Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContactRequestCreate(BaseModel):
    """Body for creating a contact request (target user_id is in URL)."""

    model_config = ConfigDict(str_strip_whitespace=True)


class RespondRequest(BaseModel):
    """Accept or reject a contact request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    action: str = Field(..., pattern="^(accept|reject)$", description="accept or reject")


class ParentApprovalRequest(BaseModel):
    """Parent approve or deny a contact request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    decision: str = Field(..., pattern="^(approve|deny)$", description="approve or deny")


class ContactResponse(BaseModel):
    """Single contact response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    target_id: UUID
    status: str
    parent_approval_status: str
    created_at: datetime


class ContactApprovalResponse(BaseModel):
    """Parent approval decision response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    parent_user_id: UUID
    decision: str
    decided_at: datetime | None = None


class ContactListResponse(BaseModel):
    """Paginated list of contacts."""

    items: list[ContactResponse]
    total: int
    page: int
    page_size: int


class ContactWithProfileResponse(BaseModel):
    """Contact with enriched requester/target profile info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    target_id: UUID
    status: str
    parent_approval_status: str
    created_at: datetime
    requester_display_name: str | None = None
    requester_age_tier: str | None = None
    requester_avatar_url: str | None = None
    target_display_name: str | None = None
    target_age_tier: str | None = None
    target_avatar_url: str | None = None


class ContactWithProfileListResponse(BaseModel):
    """Paginated list of contacts with profile info."""

    items: list[ContactWithProfileResponse]
    total: int
    page: int
    page_size: int


class BatchApprovalRequest(BaseModel):
    """Batch approve or deny multiple contact requests."""

    model_config = ConfigDict(str_strip_whitespace=True)

    contact_ids: list[UUID] = Field(..., min_length=1, description="List of contact IDs")
    decision: str = Field(..., pattern="^(approve|deny)$", description="approve or deny")


class BatchApprovalResponse(BaseModel):
    """Result of batch approval operation."""

    processed: int
    failed: int
    errors: list[dict] = Field(default_factory=list)
