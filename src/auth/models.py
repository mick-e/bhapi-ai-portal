"""Auth database models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models import JSONType, SoftDeleteMixin, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # family, school, club
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(back_populates="user", lazy="selectin")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", lazy="selectin")


class OAuthConnection(Base, UUIDMixin, TimestampMixin):
    """OAuth provider connection."""

    __tablename__ = "oauth_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, microsoft, apple
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user: Mapped["User"] = relationship(back_populates="oauth_connections")


class Session(Base, UUIDMixin):
    """User session."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_info: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
