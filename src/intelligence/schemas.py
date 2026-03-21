"""Pydantic v2 schemas for the intelligence module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
