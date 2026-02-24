"""Capture gateway Pydantic schemas."""

from datetime import datetime
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
