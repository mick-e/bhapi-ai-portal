"""Risk & safety engine Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class RiskClassification(BaseSchema):
    """Result of a single risk classification from any pipeline layer."""

    category: str = Field(description="Risk category (e.g. SELF_HARM, PII_EXPOSURE)")
    severity: str = Field(pattern="^(critical|high|medium|low)$", description="Severity level")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(description="Human-readable explanation of why the classification was made")


class RiskEventResponse(BaseSchema):
    """Risk event response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    capture_event_id: UUID | None
    category: str
    severity: str
    confidence: float
    details: dict | None
    acknowledged: bool
    acknowledged_by: UUID | None
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RiskEventListResponse(BaseSchema):
    """Paginated list of risk events."""

    items: list[RiskEventResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


class RiskConfigResponse(BaseSchema):
    """Risk config response for a single category."""

    id: UUID
    group_id: UUID
    category: str
    sensitivity: int
    enabled: bool
    custom_keywords: dict | None


class RiskConfigUpdate(BaseSchema):
    """Update risk configuration for a category."""

    sensitivity: int | None = Field(None, ge=0, le=100, description="Sensitivity threshold 0-100")
    enabled: bool | None = Field(None, description="Whether this category is enabled")
    custom_keywords: dict | None = Field(None, description="Custom keyword lists for this category")


class RiskEventAcknowledge(BaseSchema):
    """Acknowledge a risk event."""

    acknowledged_by: UUID = Field(description="User ID of the person acknowledging the event")


class ContentExcerptResponse(BaseSchema):
    """Content excerpt response (decrypted by caller)."""

    id: UUID
    risk_event_id: UUID
    encrypted_content: str
    encryption_key_id: str | None
    expires_at: datetime
    created_at: datetime
