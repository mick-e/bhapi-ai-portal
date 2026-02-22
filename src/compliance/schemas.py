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
