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
    classifier_source: str = "keyword"
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


# ---------------------------------------------------------------------------
# Safety score schemas
# ---------------------------------------------------------------------------


class SafetyScoreResponse(BaseSchema):
    """Safety score for a single member."""

    score: float = Field(ge=0, le=100, description="Safety score 0-100 (100 = safest)")
    trend: str = Field(
        pattern="^(improving|declining|stable)$",
        description="Score trend direction",
    )
    top_categories: list[str] = Field(description="Most frequent risk categories")
    risk_count_by_severity: dict[str, int] = Field(
        description="Risk event counts by severity level"
    )
    member_id: UUID
    group_id: UUID


class MemberScoreItem(BaseSchema):
    """Individual member score within a group score response."""

    member_id: UUID
    score: float = Field(ge=0, le=100)
    trend: str


class GroupScoreResponse(BaseSchema):
    """Aggregate safety score for a group."""

    average_score: float = Field(ge=0, le=100, description="Average safety score")
    group_id: UUID
    member_scores: list[MemberScoreItem] = Field(
        description="Individual member scores"
    )


class ScoreHistoryEntry(BaseSchema):
    """A single day's score in the history."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    score: float = Field(ge=0, le=100, description="Safety score for this day")


class ScoreHistoryResponse(BaseSchema):
    """Daily score history over a time period."""

    member_id: UUID
    group_id: UUID
    days: int
    history: list[ScoreHistoryEntry]


# ---------------------------------------------------------------------------
# Emotional dependency schemas
# ---------------------------------------------------------------------------


class DependencyScoreResponse(BaseSchema):
    """Emotional dependency score for a member."""

    score: int = Field(ge=0, le=100, description="Composite dependency score 0-100")
    session_duration_score: int = Field(ge=0, le=25, description="Session duration sub-score")
    frequency_score: int = Field(ge=0, le=25, description="Interaction frequency sub-score")
    attachment_language_score: int = Field(ge=0, le=25, description="Attachment language sub-score")
    time_pattern_score: int = Field(ge=0, le=25, description="Late-night usage sub-score")
    trend: str = Field(
        pattern="^(improving|stable|worsening)$",
        description="Score trend direction",
    )
    risk_factors: list[str] = Field(description="Human-readable risk factor descriptions")
    platform_breakdown: dict[str, int] = Field(
        description="Event counts per companion platform"
    )
    recommendation: str = Field(description="Parent-friendly guidance")


class DependencyHistoryEntry(BaseSchema):
    """A single week's dependency score in the history."""

    week_start: str = Field(description="Week start date YYYY-MM-DD")
    week_end: str = Field(description="Week end date YYYY-MM-DD")
    score: int = Field(ge=0, le=100, description="Dependency score for this week")


class DependencyHistoryResponse(BaseSchema):
    """Weekly dependency score history."""

    member_id: UUID
    group_id: UUID
    days: int
    history: list[DependencyHistoryEntry]


# ---------------------------------------------------------------------------
# Platform safety rating schemas
# ---------------------------------------------------------------------------


class PlatformRatingResponse(BaseSchema):
    """Safety rating for a single AI platform."""

    platform: str = Field(description="AI platform name")
    safety_score: int = Field(ge=0, le=100, description="Safety score 0-100 (100 = safest)")
    risk_level: str = Field(
        pattern="^(low|medium|high)$",
        description="Overall risk level",
    )
    categories_of_concern: list[str] = Field(
        description="Categories of safety concern for this platform"
    )
    last_updated: str = Field(description="ISO 8601 timestamp of last rating update")


class PlatformRatingsListResponse(BaseSchema):
    """List of all platform safety ratings."""

    platforms: list[PlatformRatingResponse] = Field(
        description="Safety ratings for all monitored AI platforms"
    )
