"""Groups Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from src.schemas import BaseSchema


class GroupCreate(BaseSchema):
    """Create group request."""

    name: str = Field(min_length=1, max_length=255)
    type: str = Field(pattern="^(family|school|club)$")
    settings: dict | None = None


class GroupResponse(BaseSchema):
    """Group response."""

    id: UUID
    name: str
    type: str
    owner_id: UUID
    settings: dict | None
    created_at: datetime
    member_count: int = 0


class GroupUpdate(BaseSchema):
    """Update group request."""

    name: str | None = Field(None, min_length=1, max_length=255)
    settings: dict | None = None


class MemberAdd(BaseSchema):
    """Add member to group."""

    display_name: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern="^(parent|member|school_admin|club_admin)$")
    date_of_birth: datetime | None = None
    user_id: UUID | None = None


class MemberResponse(BaseSchema):
    """Group member response."""

    id: UUID
    group_id: UUID
    user_id: UUID | None
    role: str
    display_name: str
    date_of_birth: datetime | None
    created_at: datetime


class InvitationCreate(BaseSchema):
    """Create invitation request."""

    email: EmailStr
    role: str = Field(pattern="^(parent|member|school_admin|club_admin)$")


class InvitationResponse(BaseSchema):
    """Invitation response."""

    id: UUID
    group_id: UUID
    email: str
    role: str
    token: str
    status: str
    consent_required: bool
    expires_at: datetime
    created_at: datetime


class RoleChange(BaseSchema):
    """Change member role."""

    role: str = Field(pattern="^(parent|member|school_admin|club_admin)$")


class ConsentCreate(BaseSchema):
    """Record guardian consent for a member."""

    consent_type: str = Field(pattern="^(coppa|gdpr|lgpd|au_privacy|monitoring|ai_interaction|data_collection)$")
    evidence: str | None = None


class ConsentResponse(BaseSchema):
    """Consent record response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    consent_type: str
    parent_user_id: UUID | None
    given_at: datetime
    withdrawn_at: datetime | None
    created_at: datetime


# ─── Privacy (F11) ───────────────────────────────────────────────────────────


class VisibilityRequest(BaseSchema):
    """Set member visibility."""

    visible_to: list[UUID] = Field(default_factory=list)


class VisibilityResponse(BaseSchema):
    """Member visibility response."""

    group_id: UUID
    member_id: UUID
    visible_to: list[UUID]
    is_restricted: bool


class ChildSelfViewRequest(BaseSchema):
    """Enable/configure child self-view."""

    enabled: bool = True
    sections: list[str] = Field(default_factory=list)


class ChildSelfViewResponse(BaseSchema):
    """Child self-view response."""

    group_id: UUID
    member_id: UUID
    enabled: bool
    sections: list[str]


# ─── Rewards (F14) ───────────────────────────────────────────────────────────


class RewardResponse(BaseSchema):
    """Reward response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    reward_type: str
    trigger: str
    trigger_description: str
    value: int
    earned_at: datetime
    expires_at: datetime | None
    redeemed: bool
