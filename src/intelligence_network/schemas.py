"""Intelligence Network Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContributeSignalRequest(BaseModel):
    """Raw event data contributed by a group to the network."""

    signal_type: str = Field(..., min_length=1, max_length=100, description="Type of threat signal")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$", description="Signal severity")
    pattern_data: dict[str, Any] = Field(default_factory=dict, description="Anonymized pattern details")
    description: str | None = Field(default=None, max_length=2000, description="Optional description")
    location: str | None = Field(default=None, description="Location (will be coarsened to country)")
    timestamp: str | None = Field(default=None, description="Event timestamp (will be generalized)")

    # Fields that may contain PII — the anonymizer strips these
    user_id: str | None = Field(default=None, description="Source user ID (stripped before storage)")
    email: str | None = Field(default=None, description="Source email (stripped before storage)")
    member_id: str | None = Field(default=None, description="Source member ID (stripped before storage)")
    name: str | None = Field(default=None, description="Source name (stripped before storage)")


class ThreatSignalResponse(BaseModel):
    """Anonymized threat signal returned to subscribers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    signal_type: str
    severity: str
    pattern_data: dict[str, Any]
    sample_size: int
    contributor_region: str | None
    confidence: float
    description: str | None
    feedback_helpful: int
    feedback_false_positive: int
    created_at: datetime


class SubscriptionCreate(BaseModel):
    """Opt-in preferences for the intelligence network."""

    signal_types: list[str] = Field(
        default_factory=list,
        description="Signal types to subscribe to (empty = all)",
    )
    minimum_severity: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
        description="Minimum severity to receive",
    )


class SubscriptionResponse(BaseModel):
    """Subscription status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    is_active: bool
    signal_types: list[str]
    minimum_severity: str
    created_at: datetime
    updated_at: datetime


class SignalFeedbackRequest(BaseModel):
    """Feedback on a threat signal."""

    signal_id: UUID
    is_helpful: bool
    notes: str | None = Field(default=None, max_length=1000)
