"""Auth Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from src.schemas import BaseSchema


class RegisterRequest(BaseSchema):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    account_type: str = Field(pattern="^(family|school|club)$")
    date_of_birth: datetime | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain uppercase, lowercase, and digit")
        return v


class LoginRequest(BaseSchema):
    """Login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseSchema):
    """User profile response — matches frontend User type."""

    id: UUID
    email: str
    display_name: str
    account_type: str
    group_id: UUID | None = None
    role: str | None = None
    email_verified: bool = False
    mfa_enabled: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class AuthResponse(BaseSchema):
    """Auth response with token + user data for frontend."""

    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class PasswordChangeRequest(BaseSchema):
    """Password change request."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseSchema):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation with token and new password."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class OAuthAuthorizeResponse(BaseSchema):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseSchema):
    """OAuth callback parameters."""

    code: str
    state: str


class MFASetupResponse(BaseSchema):
    """MFA setup response."""

    secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseSchema):
    """MFA verification request."""

    code: str = Field(min_length=6, max_length=6)


# ─── API Keys ────────────────────────────────────────────────────────────────


class ContactInquiryRequest(BaseSchema):
    """Contact inquiry from school/club registration page."""

    organisation: str = Field(min_length=1, max_length=255)
    contact_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    account_type: str = Field(pattern="^(school|club)$")
    estimated_members: str = Field(pattern="^(10-50|50-200|200-500|500\\+)$")
    message: str | None = Field(None, max_length=2000)


class CreateApiKeyRequest(BaseSchema):
    """Create API key request."""

    name: str | None = Field(None, max_length=255)


class ApiKeyResponse(BaseSchema):
    """API key response (key is masked)."""

    id: UUID
    name: str | None = None
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class CreateApiKeyResponse(ApiKeyResponse):
    """Create API key response — full key shown only once."""

    key: str
