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


# ---------------------------------------------------------------------------
# COPPA 2026 Dashboard
# ---------------------------------------------------------------------------


class COPPAChecklistItemResponse(BaseSchema):
    """Single COPPA checklist item."""

    id: str
    label: str
    description: str
    status: str  # complete, incomplete, warning, not_applicable
    evidence: str
    action_url: str
    regulation_ref: str


class COPPAComplianceReportResponse(BaseSchema):
    """Full COPPA compliance assessment response."""

    group_id: str
    group_name: str
    score: float
    status: str  # compliant, partial, non_compliant
    checklist: list[COPPAChecklistItemResponse]
    assessed_at: str
    last_review: str | None


class COPPAReviewResponse(BaseSchema):
    """Response after marking annual review complete."""

    group_id: str
    reviewed_at: str
    status: str


# ---------------------------------------------------------------------------
# COPPA 2026 — Third-party consent
# ---------------------------------------------------------------------------


class ThirdPartyConsentItemResponse(BaseSchema):
    """Third-party consent item response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    parent_user_id: UUID
    provider_key: str
    provider_name: str
    data_purpose: str
    consented: bool
    consented_at: datetime | None
    withdrawn_at: datetime | None
    created_at: datetime


class ThirdPartyConsentUpdate(BaseSchema):
    """Update consent for a specific third-party provider."""

    provider_key: str = Field(max_length=50)
    consented: bool


class ThirdPartyConsentBulkUpdate(BaseSchema):
    """Bulk update third-party consent (all providers at once)."""

    member_id: UUID
    consents: list[ThirdPartyConsentUpdate]


class RefusePartialCollectionRequest(BaseSchema):
    """Toggle refuse-partial-collection: consent to collection but refuse 3rd-party sharing."""

    member_id: UUID
    refuse_third_party_sharing: bool


# ---------------------------------------------------------------------------
# COPPA 2026 — Retention policies
# ---------------------------------------------------------------------------


class RetentionPolicyResponse(BaseSchema):
    """Retention policy response."""

    id: UUID
    group_id: UUID
    data_type: str
    retention_days: int
    description: str
    auto_delete: bool
    last_cleanup_at: datetime | None
    records_deleted: int
    created_at: datetime


class RetentionPolicyUpdate(BaseSchema):
    """Update a retention policy."""

    data_type: str = Field(max_length=50)
    retention_days: int = Field(ge=30, le=3650)
    auto_delete: bool = True


class RetentionDisclosureResponse(BaseSchema):
    """Parent-facing retention disclosure."""

    group_id: str
    generated_at: str
    summary: str
    policies: list[dict]


# ---------------------------------------------------------------------------
# COPPA 2026 — Push notification consent
# ---------------------------------------------------------------------------


class PushNotificationConsentResponse(BaseSchema):
    """Push notification consent response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    parent_user_id: UUID
    notification_type: str
    consented: bool
    consented_at: datetime | None
    withdrawn_at: datetime | None
    created_at: datetime


class PushNotificationConsentUpdate(BaseSchema):
    """Update push notification consent."""

    member_id: UUID
    notification_type: str = Field(
        pattern="^(risk_alerts|activity_summaries|weekly_reports|all)$"
    )
    consented: bool


# ---------------------------------------------------------------------------
# COPPA 2026 — Video verification (enhanced VPC)
# ---------------------------------------------------------------------------


class VideoVerificationResponse(BaseSchema):
    """Video verification response."""

    id: UUID
    group_id: UUID
    parent_user_id: UUID
    verification_method: str
    status: str
    yoti_session_id: str | None
    verification_score: float | None
    verified_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class VideoVerificationCreate(BaseSchema):
    """Initiate video verification."""

    verification_method: str = Field(
        pattern="^(video_call|yoti_id_check|video_selfie)$"
    )
