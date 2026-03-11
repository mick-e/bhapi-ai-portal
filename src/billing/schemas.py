"""Billing Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class SubscribeRequest(BaseSchema):
    """Create subscription request."""

    group_id: UUID
    plan_type: str = Field(pattern="^(free|starter|family|school|enterprise)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")
    stripe_payment_method_id: str | None = None


class SubscriptionStatus(BaseSchema):
    """Subscription status response."""

    id: UUID
    group_id: UUID
    plan_type: str
    billing_cycle: str
    status: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    trial_end: datetime | None
    current_period_end: datetime | None
    created_at: datetime


class ProviderConnect(BaseSchema):
    """Connect LLM provider account request."""

    group_id: UUID
    provider: str = Field(pattern="^(openai|google|microsoft|anthropic|xai)$")
    api_key: str = Field(min_length=1, max_length=512)


class LLMAccountResponse(BaseSchema):
    """LLM account response (credentials excluded)."""

    id: UUID
    group_id: UUID
    provider: str
    last_synced: datetime | None
    status: str
    created_at: datetime


class SpendRecordResponse(BaseSchema):
    """Spend record response."""

    id: UUID
    group_id: UUID
    llm_account_id: UUID
    member_id: UUID | None
    period_start: datetime
    period_end: datetime
    amount: float
    currency: str
    token_count: int | None
    model: str | None
    created_at: datetime


class SpendSummary(BaseSchema):
    """Aggregated spend summary."""

    group_id: UUID
    period_start: datetime
    period_end: datetime
    total_amount: float
    currency: str
    by_provider: dict[str, float] = Field(default_factory=dict)
    by_member: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)
    record_count: int = 0


class ThresholdConfig(BaseSchema):
    """Create/update budget threshold request."""

    group_id: UUID
    member_id: UUID | None = None
    type: str = Field(pattern="^(soft|hard)$")
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", max_length=3)
    notify_at: list[int] = Field(default=[50, 80, 100])


class ThresholdResponse(BaseSchema):
    """Budget threshold response."""

    id: UUID
    group_id: UUID
    member_id: UUID | None
    type: str
    amount: float
    currency: str
    notify_at: list[int] | None
    created_at: datetime


class CheckoutRequest(BaseSchema):
    """Create Stripe checkout session request."""

    plan_type: str = Field(pattern="^(family|school|club)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")


class CheckoutResponse(BaseSchema):
    """Stripe checkout session response."""

    session_id: str
    url: str


class PortalResponse(BaseSchema):
    """Stripe billing portal response."""

    url: str


class TrialStatusResponse(BaseSchema):
    """Trial status for the current group."""

    is_active: bool
    is_trial: bool
    is_locked: bool
    days_remaining: int
    trial_end: datetime | None
    plan: str
    contact_email: str = "contactus@bhapi.io"


class VendorRiskResponse(BaseSchema):
    """Vendor risk assessment response."""

    provider: str
    name: str
    overall_score: int
    grade: str
    category_scores: dict[str, int]
    recommendations: list[str]


class EnvelopeCreate(BaseSchema):
    """Create a spend envelope (budget allocation)."""

    group_id: UUID
    member_id: UUID | None = None
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", max_length=3)
    period: str = Field(default="monthly", pattern="^(daily|weekly|monthly)$")


class EnvelopeResponse(BaseSchema):
    """Spend envelope response."""

    id: UUID
    group_id: UUID
    member_id: UUID | None
    amount: float
    currency: str
    period: str
    spent: float = 0.0
    remaining: float = 0.0
    created_at: datetime


# ---------------------------------------------------------------------------
# Platform Safety Ratings
# ---------------------------------------------------------------------------


class PlatformSafetyRatingResponse(BaseSchema):
    """Safety rating for a single AI platform."""

    key: str
    name: str
    overall_grade: str
    min_age_recommended: int
    has_parental_controls: bool
    has_content_filters: bool
    data_retention_days: int
    coppa_compliant: bool
    known_incidents: int
    strengths: list[str]
    concerns: list[str]
    last_updated: str


class PlatformSafetyRecommendationResponse(PlatformSafetyRatingResponse):
    """Safety rating with age-based recommendation."""

    recommendation: str  # recommended, use_with_caution, not_recommended
