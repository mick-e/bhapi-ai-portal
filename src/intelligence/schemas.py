"""Pydantic v2 schemas for the intelligence module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Correlation Rules
# ---------------------------------------------------------------------------


class CorrelationRuleCreate(BaseModel):
    """Create a correlation rule."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    condition: dict = Field(..., description="JSON condition with signals, logic, time_window_hours")
    action_severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")
    notification_type: str = Field(default="alert", pattern=r"^(alert|email|push|sms)$")
    age_tier_filter: str | None = Field(default=None, pattern=r"^(young|preteen|teen)$")
    enabled: bool = True


class CorrelationRuleUpdate(BaseModel):
    """Update a correlation rule (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    condition: dict | None = None
    action_severity: str | None = Field(default=None, pattern=r"^(low|medium|high|critical)$")
    notification_type: str | None = Field(default=None, pattern=r"^(alert|email|push|sms)$")
    age_tier_filter: str | None = Field(default=None, pattern=r"^(young|preteen|teen)$")
    enabled: bool | None = None


class CorrelationRuleResponse(BaseModel):
    """Correlation rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    condition: dict
    action_severity: str
    notification_type: str
    age_tier_filter: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CorrelationRuleListResponse(BaseModel):
    """List of correlation rules."""

    items: list[CorrelationRuleResponse]
    total: int


# ---------------------------------------------------------------------------
# Enriched Alerts
# ---------------------------------------------------------------------------


class EnrichedAlertResponse(BaseModel):
    """Enriched alert response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alert_id: UUID
    correlation_rule_id: UUID | None = None
    correlation_context: str
    contributing_signals: dict
    unified_risk_score: float
    confidence: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Social Graph Edge
# ---------------------------------------------------------------------------


class SocialGraphEdgeCreate(BaseModel):
    """Create a social graph edge."""

    source_id: UUID
    target_id: UUID
    edge_type: str = Field(..., pattern=r"^(contact|follow|message|mention)$")
    weight: float = Field(default=1.0, ge=0.0)
    last_interaction: datetime | None = None


class SocialGraphEdgeResponse(BaseModel):
    """Social graph edge response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    target_id: UUID
    edge_type: str
    weight: float
    last_interaction: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Abuse Signal
# ---------------------------------------------------------------------------


class AbuseSignalCreate(BaseModel):
    """Create an abuse signal."""

    member_id: UUID
    signal_type: str = Field(
        ...,
        pattern=r"^(age_gap|isolation|influence|farming|age_misrepresentation|account_farming|coordinated_harassment|report_abuse|content_manipulation)$",
    )
    severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")
    details: dict | None = None


class AbuseSignalResponse(BaseModel):
    """Abuse signal response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    signal_type: str
    severity: str
    details: dict | None = None
    resolved: bool
    resolved_at: datetime | None = None
    created_at: datetime


class AbuseSignalListResponse(BaseModel):
    """Paginated list of abuse signals."""

    items: list[AbuseSignalResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


# ---------------------------------------------------------------------------
# Graph Analysis Results
# ---------------------------------------------------------------------------


class AgeGapFlag(BaseModel):
    """A flagged age-inappropriate contact."""

    contact_member_id: UUID
    source_age: int
    target_age: int
    age_gap: int
    edge_type: str
    severity: str


class GraphAnalysisResponse(BaseModel):
    """Result of graph analysis for a member."""

    member_id: UUID
    age_gap_flags: list[AgeGapFlag] = Field(default_factory=list)
    total_contacts: int = 0
    flagged_count: int = 0


class IsolationIndicator(BaseModel):
    """An indicator of social isolation."""

    indicator: str
    description: str
    weight: float


class IsolationResponse(BaseModel):
    """Result of isolation detection for a member."""

    member_id: UUID
    isolation_score: float = Field(ge=0, le=100)
    indicators: list[IsolationIndicator] = Field(default_factory=list)
    contact_count: int = 0
    interaction_count: int = 0


class Influencer(BaseModel):
    """An influencer in the member's social graph."""

    member_id: UUID
    influence_score: float
    edge_count: int
    edge_types: list[str]


class InfluenceResponse(BaseModel):
    """Result of influence mapping for a member."""

    member_id: UUID
    influencers: list[Influencer] = Field(default_factory=list)
    influence_score: float = 0.0
    total_connections: int = 0


# ---------------------------------------------------------------------------
# Behavioral Baseline
# ---------------------------------------------------------------------------


class BehavioralBaselineResponse(BaseModel):
    """Behavioral baseline response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    window_days: int
    metrics: dict | None = None
    computed_at: datetime
    sample_count: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Unified Risk Scoring
# ---------------------------------------------------------------------------


class SourceScore(BaseModel):
    """Sub-score from a single signal source."""

    source: str  # ai_monitoring, social_behavior, device_usage, location
    sub_score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_contribution: float


class UnifiedRiskScoreResponse(BaseModel):
    """Unified risk score response for a child."""

    child_id: UUID
    unified_score: float = Field(ge=0, le=100)
    confidence: str  # low, medium, high
    trend: str  # increasing, stable, decreasing
    age_tier: str  # young, preteen, teen


class ScoreBreakdownResponse(BaseModel):
    """Per-source score breakdown."""

    child_id: UUID
    sources: list[SourceScore]
    unified_score: float = Field(ge=0, le=100)


class ScoreDataPoint(BaseModel):
    """A single daily score data point."""

    date: str  # ISO date YYYY-MM-DD
    score: float = Field(ge=0, le=100)


class ScoreHistoryResponse(BaseModel):
    """Historical score series for a child."""

    child_id: UUID
    history: list[ScoreDataPoint]
