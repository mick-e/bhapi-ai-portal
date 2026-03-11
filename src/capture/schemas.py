"""Capture gateway Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class EventPayload(BaseSchema):
    """Base event payload from any capture channel."""

    group_id: UUID
    member_id: UUID
    platform: str = Field(pattern="^(chatgpt|gemini|copilot|claude|grok)$")
    session_id: str = Field(min_length=1, max_length=255)
    event_type: str = Field(pattern="^(prompt|response|session_start|session_end)$")
    timestamp: datetime
    content: str | None = None
    metadata: dict | None = None


class ExtensionEvent(EventPayload):
    """Event from browser extension."""

    extension_id: str
    hmac_signature: str


class DNSEvent(BaseSchema):
    """Event from DNS proxy."""

    group_id: UUID
    member_id: UUID
    domain: str
    query_type: str = "A"
    timestamp: datetime
    client_ip: str


class APIWebhookEvent(EventPayload):
    """Event from LLM API webhook."""

    provider_event_id: str | None = None
    api_key_id: str | None = None


class CaptureEventResponse(BaseSchema):
    """Capture event response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    platform: str
    session_id: str
    event_type: str
    timestamp: datetime
    content: str | None = None
    source_channel: str
    risk_processed: bool
    created_at: datetime


class EnrichedEventResponse(BaseSchema):
    """Enriched capture event response with member name and risk level."""

    id: UUID
    group_id: UUID
    member_id: UUID
    member_name: str = ""
    provider: str
    model: str = ""
    event_type: str
    prompt_preview: str = ""
    response_preview: str = ""
    token_count: int = 0
    cost_usd: float = 0.0
    risk_level: str = "low"
    flagged: bool = False
    timestamp: datetime


class ContentCaptureRequest(BaseSchema):
    """Enhanced capture event with content."""

    group_id: UUID
    member_id: UUID
    platform: str
    event_type: str = "conversation"
    content: str  # Plain text content to be encrypted
    content_type: str = "prompt"  # prompt, response, conversation
    metadata: dict | None = None


class ContentCaptureResponse(BaseSchema):
    """Content capture response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    platform: str
    content_type: str | None
    enhanced_monitoring: bool
    created_at: datetime


class SetupCodeCreate(BaseSchema):
    """Request to create a setup code for extension pairing."""

    group_id: UUID
    member_id: UUID
    device_name: str | None = None


class SetupCodeResponse(BaseSchema):
    """Response after creating a setup code."""

    id: UUID
    code: str
    group_id: UUID
    member_id: UUID
    expires_at: datetime
    created_at: datetime


class PairRequest(BaseSchema):
    """Request to pair an extension using a setup code."""

    setup_code: str


class PairResponse(BaseSchema):
    """Response after successfully pairing an extension."""

    group_id: str
    member_id: str
    signing_secret: str


class DeviceRegisterRequest(BaseSchema):
    """Device registration request."""

    group_id: UUID
    member_id: UUID
    device_name: str = Field(min_length=1, max_length=255)
    setup_code: str = Field(min_length=6, max_length=20)


class DeviceResponse(BaseSchema):
    """Device registration response."""

    id: UUID
    group_id: UUID
    member_id: UUID
    device_name: str
    setup_code: str
    extension_id: str | None
    registered_at: datetime


# ─── Conversation Summary Schemas ────────────────────────────────────────────


class ConversationSummaryResponse(BaseSchema):
    """Conversation summary response for parents."""

    id: UUID
    group_id: UUID
    member_id: UUID
    capture_event_id: UUID | None = None
    platform: str
    date: date
    topics: list = Field(default_factory=list)
    emotional_tone: str
    risk_flags: list = Field(default_factory=list)
    key_quotes: list = Field(default_factory=list)
    action_needed: bool
    action_reason: str | None = None
    summary_text: str
    detail_level: str
    llm_model: str
    content_hash: str
    created_at: datetime
    updated_at: datetime


class SummaryListRequest(BaseSchema):
    """Query parameters for listing summaries."""

    group_id: UUID | None = None
    member_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SummarizeRequest(BaseSchema):
    """Request to trigger manual summarization for an event."""

    event_id: UUID
    member_age: int | None = None
