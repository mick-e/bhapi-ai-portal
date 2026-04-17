"""FERPA module Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class EducationalRecordCreate(BaseSchema):
    """Create a FERPA educational record designation."""

    member_id: UUID
    record_type: str = Field(max_length=50)
    title: str = Field(max_length=255, min_length=1)
    description: str | None = None
    is_directory_info: bool = False
    classification: str = Field(default="protected", max_length=30)
    metadata_json: dict | None = None


class AccessLogCreate(BaseSchema):
    """Log access to an educational record (34 CFR 99.32)."""

    record_id: UUID
    access_type: str = Field(max_length=30)
    purpose: str = Field(max_length=500, min_length=1)
    legitimate_interest: str | None = Field(default=None, max_length=100)


class AnnualNotificationCreate(BaseSchema):
    """Send annual FERPA notification."""

    school_year: str = Field(max_length=9, min_length=9, pattern=r"^\d{4}-\d{4}$")
    template_version: int = Field(default=1, ge=1)


class DataSharingAgreementCreate(BaseSchema):
    """Create a third-party data sharing agreement."""

    third_party_name: str = Field(max_length=255, min_length=1)
    purpose: str = Field(max_length=500, min_length=1)
    data_elements: dict
    legal_basis: str = Field(max_length=50)
    effective_date: datetime
    expiration_date: datetime | None = None
    terms: dict | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class EducationalRecordResponse(BaseSchema):
    """Educational record response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    record_type: str
    title: str
    description: str | None = None
    is_directory_info: bool
    classification: str
    created_by: UUID
    metadata_json: dict | None = None
    created_at: datetime
    updated_at: datetime


class AccessLogResponse(BaseSchema):
    """Access log response."""

    id: UUID
    group_id: UUID
    record_id: UUID
    accessor_user_id: UUID
    access_type: str
    purpose: str
    legitimate_interest: str | None = None
    accessed_at: datetime
    created_at: datetime


class AnnualNotificationResponse(BaseSchema):
    """Annual notification response."""

    id: UUID
    group_id: UUID
    school_year: str
    sent_at: datetime
    template_version: int
    recipient_count: int
    notification_method: str
    created_at: datetime


class DataSharingAgreementResponse(BaseSchema):
    """Data sharing agreement response."""

    id: UUID
    group_id: UUID
    third_party_name: str
    purpose: str
    data_elements: dict
    legal_basis: str
    status: str
    effective_date: datetime
    expiration_date: datetime | None = None
    created_by: UUID
    terms: dict | None = None
    created_at: datetime
    updated_at: datetime
