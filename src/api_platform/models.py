"""API Platform database models — OAuth clients, tokens, tiers, webhooks, usage."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class OAuthClient(Base, UUIDMixin, TimestampMixin):
    """Registered API client (partner or school)."""

    __tablename__ = "oauth_clients"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_uris: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # list of URIs
    scopes: Mapped[dict] = mapped_column(JSONType, nullable=False)  # list of allowed scopes
    tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="school",
    )  # school, partner, enterprise
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OAuthToken(Base, UUIDMixin, TimestampMixin):
    """Issued OAuth token."""

    __tablename__ = "oauth_tokens"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    access_token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True,
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True,
    )
    scopes: Mapped[dict] = mapped_column(JSONType, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class APIKeyTier(Base, UUIDMixin, TimestampMixin):
    """API rate limit tier configuration."""

    __tablename__ = "api_key_tiers"

    name: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True,
    )  # school, partner, enterprise
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    max_webhooks: Mapped[int] = mapped_column(Integer, nullable=False)
    price_monthly: Mapped[float | None] = mapped_column(Float, nullable=True)


class PlatformWebhookEndpoint(Base, UUIDMixin, TimestampMixin):
    """Registered webhook endpoint for a platform API client."""

    __tablename__ = "platform_webhook_endpoints"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[dict] = mapped_column(JSONType, nullable=False)  # list of event types
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PlatformWebhookDelivery(Base, UUIDMixin, TimestampMixin):
    """Log of platform webhook delivery attempts."""

    __tablename__ = "platform_webhook_deliveries"
    __table_args__ = (
        Index(
            "ix_platform_wh_deliveries_endpoint_created",
            "endpoint_id",
            "created_at",
        ),
    )

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class APIUsageRecord(Base, UUIDMixin, TimestampMixin):
    """API usage tracking per client per day."""

    __tablename__ = "api_usage_records"
    __table_args__ = (
        Index("ix_api_usage_client_date", "client_id", "date", unique=True),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    webhook_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
