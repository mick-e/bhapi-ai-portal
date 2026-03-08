"""Compliance Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class DataRequestCreate(BaseSchema):
    """Create data deletion/export request."""

    request_type: str = Field(
        pattern="^(full_deletion|data_export|rectification)$"
    )


class DataRequestStatus(BaseSchema):
    """Data request status response."""

    id: UUID
    user_id: UUID
    request_type: str
    status: str
    completed_at: datetime | None
    created_at: datetime


class ConsentResponse(BaseSchema):
    """Consent record response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    consent_type: str
    parent_user_id: UUID | None
    given_at: datetime
    withdrawn_at: datetime | None
    ip_address: str | None
    evidence: str | None
    created_at: datetime


class ConsentWithdrawRequest(BaseSchema):
    """Request to withdraw consent (GDPR Article 7(3))."""

    group_id: UUID
    member_id: UUID
    consent_type: str | None = None  # None = withdraw all active consents


class AuditEntryResponse(BaseSchema):
    """Audit log entry response."""

    id: UUID
    group_id: UUID
    actor_id: UUID
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# EU AI Act — human review and appeals
# ---------------------------------------------------------------------------


class HumanReviewResponse(BaseSchema):
    """Human review request response."""

    id: UUID
    risk_event_id: UUID
    group_id: UUID
    requested_by: UUID
    status: str
    reviewer_id: UUID | None
    reviewed_at: datetime | None
    decision: str | None
    notes: str | None
    created_at: datetime


class AppealSubmit(BaseSchema):
    """Submit an appeal against an automated risk classification."""

    reason: str = Field(min_length=1, max_length=2000)


class AppealResolve(BaseSchema):
    """Resolve an appeal (admin action)."""

    resolution: str = Field(pattern="^(upheld|overturned|modified)$")
    notes: str | None = Field(None, max_length=2000)


class AppealResponse(BaseSchema):
    """Appeal record response."""

    id: UUID
    risk_event_id: UUID
    group_id: UUID
    user_id: UUID
    reason: str
    status: str
    resolved_by: UUID | None
    resolution: str | None
    resolution_notes: str | None
    resolved_at: datetime | None
    created_at: datetime
