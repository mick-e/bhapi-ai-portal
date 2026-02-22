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
    """User profile response."""

    id: UUID
    email: str
    display_name: str
    account_type: str
    email_verified: bool
    mfa_enabled: bool
    created_at: datetime


class PasswordChangeRequest(BaseSchema):
    """Password change request."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseSchema):
    """Password reset request."""

    email: EmailStr


class MFASetupResponse(BaseSchema):
    """MFA setup response."""

    secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseSchema):
    """MFA verification request."""

    code: str = Field(min_length=6, max_length=6)
