"""Application configuration using pydantic-settings."""

import warnings
from functools import lru_cache
from typing import Literal

import structlog
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://bhapi:bhapi_dev_password@localhost:5432/bhapi"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """Convert postgres:// to postgresql+asyncpg:// for asyncpg compatibility."""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis (optional — graceful degradation if None)
    redis_url: str | None = Field(default="redis://localhost:6379/0")

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production")

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Session
    session_timeout_hours: int = 24
    cookie_domain: str | None = None

    # Rate Limiting
    rate_limit_requests: int = 1000
    rate_limit_window_seconds: int = 60
    rate_limit_fail_open: bool = False

    # Stripe
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_publishable_key: str | None = None

    # Capture HMAC validation (disabled in dev/test for convenience)
    capture_hmac_secret: str | None = None
    capture_hmac_enabled: bool = False

    # Safety classifier mode: keyword_only, vertex_ai, auto (try vertex_ai, fallback to keyword)
    safety_classifier_mode: Literal["keyword_only", "vertex_ai", "auto"] = "keyword_only"
    vertex_ai_model: str = "gemini-1.5-flash"
    vertex_ai_location: str = "us-central1"

    # Email
    sendgrid_api_key: str | None = None

    # GCP
    gcp_project_id: str | None = None

    # CORS — comma-separated origins (overrides defaults when set)
    cors_origins: str | None = None

    # Encryption
    encryption_key: str | None = None  # Optional separate key for Fernet; falls back to secret_key

    # App
    app_name: str = "Bhapi AI Portal"
    app_version: str = "0.1.0"

    @field_validator("secret_key", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Warn if secret key is a placeholder."""
        if v.startswith("dev-secret-key"):
            warnings.warn(
                "SECRET_KEY appears to be a placeholder value. "
                "Set a secure random value (min 32 chars) for production use.",
                stacklevel=2,
            )
        return v

    @computed_field
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @computed_field
    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    def validate_production_config(self) -> None:
        """Validate configuration for production safety."""
        if not self.is_production:
            return

        weak_patterns = ["changeme", "secret", "dev-secret", "placeholder", "default"]
        secret_lower = self.secret_key.lower()
        for pattern in weak_patterns:
            if pattern in secret_lower:
                raise ValueError(
                    f"SECURITY ERROR: SECRET_KEY contains weak pattern '{pattern}'. "
                    "Set SECRET_KEY to a cryptographically random value (min 32 chars)."
                )
        if len(self.secret_key) < 32:
            raise ValueError(
                f"SECURITY ERROR: SECRET_KEY too short ({len(self.secret_key)} chars, min 32)."
            )

        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.database_url)
            db_password = (parsed.password or "").lower()
        except Exception:
            db_password = ""
        weak_passwords = ["bhapi_dev_password", "postgres", "password", "changeme"]
        for pw in weak_passwords:
            if db_password == pw:
                raise ValueError(
                    f"SECURITY ERROR: DATABASE_URL contains weak password '{pw}'."
                )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    if settings.is_production and settings.secret_key.startswith("dev-secret-key"):
        raise ValueError(
            "SECURITY ERROR: SECRET_KEY is too weak for production. "
            "Set SECRET_KEY to a secure random value (min 32 chars)."
        )
    if settings.is_production and "localhost" in settings.database_url:
        raise ValueError(
            "CONFIG ERROR: DATABASE_URL points to localhost in production."
        )
    settings.validate_production_config()
    return settings
