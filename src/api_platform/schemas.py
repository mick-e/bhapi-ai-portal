"""Pydantic v2 schemas for the API platform module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# OAuth Client
# ---------------------------------------------------------------------------

VALID_SCOPES = {
    "read:alerts",
    "read:compliance",
    "read:activity",
    "write:webhooks",
    "read:risk_scores",
    "read:checkins",
    "read:screen_time",
}

VALID_TIERS = {"school", "partner", "enterprise"}


class OAuthClientCreate(BaseModel):
    """Schema for registering a new OAuth client."""

    name: str = Field(..., min_length=1, max_length=100)
    redirect_uris: list[str] | None = Field(default=None, max_length=10)
    scopes: list[str] = Field(..., min_length=1)
    tier: str = Field(default="school", pattern=r"^(school|partner|enterprise)$")


class OAuthClientResponse(BaseModel):
    """Schema for OAuth client responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    client_id: str
    redirect_uris: list | None = None
    scopes: list
    tier: str
    owner_id: UUID
    is_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OAuthClientCreateResponse(OAuthClientResponse):
    """OAuth client creation response — includes the plaintext secret (shown once)."""

    client_secret: str


class OAuthClientListResponse(BaseModel):
    """Paginated list of OAuth clients."""

    items: list[OAuthClientResponse]
    total: int


# ---------------------------------------------------------------------------
# Authorization + Token
# ---------------------------------------------------------------------------


class AuthorizationRequest(BaseModel):
    """OAuth authorization code request (PKCE)."""

    client_id: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)
    scope: str = Field(..., min_length=1)
    state: str = Field(..., min_length=8, max_length=128)
    code_challenge: str = Field(..., min_length=43, max_length=128)
    code_challenge_method: str = Field(default="S256", pattern=r"^S256$")


class AuthorizationResponse(BaseModel):
    """OAuth authorization code response."""

    code: str
    state: str
    expires_in: int = 600  # 10 minutes


class TokenRequest(BaseModel):
    """OAuth token exchange request."""

    grant_type: str = Field(..., pattern=r"^authorization_code$")
    code: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)
    code_verifier: str = Field(..., min_length=43, max_length=128)


class TokenRefreshRequest(BaseModel):
    """OAuth token refresh request."""

    grant_type: str = Field(..., pattern=r"^refresh_token$")
    refresh_token: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)


class TokenRevokeRequest(BaseModel):
    """Token revocation request."""

    token: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """OAuth token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    refresh_token: str | None = None
    scope: str


# ---------------------------------------------------------------------------
# OAuth Token
# ---------------------------------------------------------------------------


class OAuthTokenResponse(BaseModel):
    """Schema for token record responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    user_id: UUID
    scopes: list
    expires_at: datetime
    refresh_expires_at: datetime | None = None
    revoked: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Webhook Endpoints
# ---------------------------------------------------------------------------


class WebhookEndpointCreate(BaseModel):
    """Schema for registering a webhook endpoint."""

    url: str = Field(..., min_length=1, max_length=500, pattern=r"^https?://")
    events: list[str] = Field(..., min_length=1)
    secret: str = Field(..., min_length=16, max_length=128)


class WebhookEndpointResponse(BaseModel):
    """Schema for webhook endpoint responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    url: str
    events: list
    is_active: bool
    created_at: datetime


class WebhookEndpointListResponse(BaseModel):
    """List of webhook endpoints."""

    items: list[WebhookEndpointResponse]
    total: int


class WebhookDeliveryResponse(BaseModel):
    """Schema for a single webhook delivery attempt."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint_id: UUID
    event_type: str
    payload: dict
    status_code: int | None = None
    response_time_ms: int | None = None
    attempt_count: int
    delivered: bool
    error: str | None = None
    created_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    """Paginated delivery log for a webhook endpoint."""

    items: list[WebhookDeliveryResponse]
    total: int


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


class UsageDayResponse(BaseModel):
    """Usage for a single day."""

    model_config = ConfigDict(from_attributes=True)

    date: str
    request_count: int
    webhook_deliveries: int


class UsageResponse(BaseModel):
    """Usage metrics response."""

    client_id: UUID
    days: list[UsageDayResponse]
    total_requests: int
    total_webhook_deliveries: int


# ---------------------------------------------------------------------------
# API Key Tier
# ---------------------------------------------------------------------------


class APIKeyTierResponse(BaseModel):
    """Schema for tier configuration responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rate_limit_per_hour: int
    max_webhooks: int
    price_monthly: float | None = None
    created_at: datetime
