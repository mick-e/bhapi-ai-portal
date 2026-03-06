"""Auth API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.oauth import (
    SUPPORTED_PROVIDERS,
    exchange_code_for_tokens,
    find_or_create_oauth_user,
    get_authorization_url,
    get_oauth_user_info,
)
from src.auth.schemas import (
    ApiKeyResponse,
    AuthResponse,
    ContactInquiryRequest,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    LoginRequest,
    OAuthAuthorizeResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from src.auth.service import (
    authenticate_user,
    confirm_email,
    create_access_token,
    create_api_key,
    create_session,
    delete_user_account,
    get_user_by_id,
    list_api_keys,
    register_user,
    request_password_reset,
    reset_password,
    revoke_api_key,
    send_verification_email,
    user_to_profile,
)
from src.config import get_settings
from src.constants import SESSION_COOKIE_NAME
from src.database import get_db
from src.exceptions import ValidationError
from src.schemas import GroupContext

settings = get_settings()
router = APIRouter()


def _set_session_cookie(response: Response, session_token: str) -> None:
    """Set the session cookie with consistent security attributes."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_timeout_hours * 3600,
        domain=settings.cookie_domain,
    )


async def _create_auth_response(
    db: AsyncSession, user_id: str, response: Response,
) -> AuthResponse:
    """Create access token + session cookie and return AuthResponse with user data."""
    access_token = create_access_token({"sub": user_id})
    session_token = await create_session(db, UUID(user_id))
    _set_session_cookie(response, session_token)

    # Fetch user + group context for the response
    uid = UUID(user_id)
    user = await get_user_by_id(db, uid)

    from sqlalchemy import select as sa_select
    from src.groups.models import GroupMember
    result = await db.execute(
        sa_select(GroupMember.group_id, GroupMember.role)
        .where(GroupMember.user_id == uid)
        .limit(1)
    )
    row = result.first()
    group_id = row.group_id if row else None
    role = row.role if row else None

    profile = user_to_profile(user, group_id=group_id, role=role)
    return AuthResponse(access_token=access_token, user=profile)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Register a new user account, auto-create group, and return token."""
    user = await register_user(db, data)

    # Auto-create a group for the user
    from src.groups.schemas import GroupCreate
    from src.groups.service import create_group
    group_name = f"{data.display_name}'s {data.account_type.capitalize()}"
    await create_group(db, user.id, GroupCreate(name=group_name, type=data.account_type))

    # Send verification email (non-blocking — don't fail registration on email error)
    try:
        await send_verification_email(user)
    except Exception:
        pass  # Logged in send_verification_email

    return await _create_auth_response(db, str(user.id), response)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    user = await authenticate_user(db, data.email, data.password)

    return await _create_auth_response(db, str(user.id), response)


@router.post("/logout", status_code=204)
async def logout(response: Response, db: AsyncSession = Depends(get_db)):
    """Logout and invalidate session."""
    response.delete_cookie(SESSION_COOKIE_NAME)
    return None


@router.get("/me", response_model=UserProfile)
async def get_me(
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Get current user profile with group context."""
    user = await get_user_by_id(db, auth.user_id)
    return user_to_profile(user, group_id=auth.group_id, role=auth.role)


@router.patch("/me", response_model=UserProfile)
async def update_me(
    data: dict,
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Update current user profile."""
    user = await get_user_by_id(db, auth.user_id)
    if "display_name" in data and data["display_name"]:
        user.display_name = data["display_name"]
    if "email" in data and data["email"]:
        user.email = data["email"]
    await db.flush()
    await db.refresh(user)
    return user_to_profile(user, group_id=auth.group_id, role=auth.role)


@router.post("/password/reset", status_code=202)
async def request_reset(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Request a password reset email."""
    await request_password_reset(db, data.email)
    # Always return 202 to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password/reset/confirm", status_code=200)
async def confirm_reset(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Confirm password reset with token and new password."""
    await reset_password(db, data.token, data.new_password)
    return {"message": "Password has been reset successfully"}


@router.post("/verify-email", status_code=200)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify email address with token."""
    user = await confirm_email(db, token)
    return {"message": "Email verified successfully", "email": user.email}


@router.delete("/account", status_code=204)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Delete user account (GDPR Article 17)."""
    await delete_user_account(db, auth.user_id)
    return None


# ---------------------------------------------------------------------------
# Contact Inquiry (public — no auth required)
# ---------------------------------------------------------------------------


@router.post("/contact-inquiry", status_code=202)
async def contact_inquiry(data: ContactInquiryRequest):
    """Receive a contact inquiry from the school/club registration form."""
    import structlog
    from src.email.service import send_email

    log = structlog.get_logger()

    subject = f"[Bhapi] New {data.account_type.capitalize()} Inquiry from {data.organisation}"
    html_content = (
        f"<h2>New {data.account_type.capitalize()} Inquiry</h2>"
        f"<p><strong>Organisation:</strong> {data.organisation}</p>"
        f"<p><strong>Contact:</strong> {data.contact_name}</p>"
        f"<p><strong>Email:</strong> {data.email}</p>"
        f"<p><strong>Account Type:</strong> {data.account_type}</p>"
        f"<p><strong>Estimated Members:</strong> {data.estimated_members}</p>"
        f"<p><strong>Message:</strong> {data.message or '(none)'}</p>"
    )

    sent = await send_email(
        to_email="sales@bhapi.ai",
        subject=subject,
        html_content=html_content,
        from_email="noreply@bhapi.ai",
    )

    if not sent:
        log.warning("contact_inquiry_email_failed", email=data.email, org=data.organisation)

    return {"message": "Thank you for your interest! Our team will be in touch within 1 business day."}


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_keys(
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """List all active API keys for the current user."""
    keys = await list_api_keys(db, auth.user_id)
    return keys


@router.post("/api-keys", response_model=CreateApiKeyResponse, status_code=201)
async def generate_key(
    data: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Generate a new API key. The full key is only returned once."""
    api_key, raw_key = await create_api_key(
        db, auth.user_id, auth.group_id, name=data.name,
    )
    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=raw_key,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Revoke an API key."""
    await revoke_api_key(db, key_id, auth.user_id)
    return None


# ---------------------------------------------------------------------------
# OAuth SSO endpoints
# ---------------------------------------------------------------------------


@router.get("/oauth/{provider}/authorize", response_model=OAuthAuthorizeResponse)
async def oauth_authorize(provider: str):
    """Get OAuth authorization URL for a provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValidationError(f"Unsupported provider: {provider}. Supported: {', '.join(sorted(SUPPORTED_PROVIDERS))}")

    authorization_url, state = get_authorization_url(provider)
    return OAuthAuthorizeResponse(authorization_url=authorization_url, state=state)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback — exchange code for tokens and create session."""
    if provider not in SUPPORTED_PROVIDERS:
        raise ValidationError(f"Unsupported provider: {provider}")

    # Exchange authorization code for tokens
    token_data = await exchange_code_for_tokens(provider, code)
    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    id_token = token_data.get("id_token")

    # Fetch user info from provider
    user_info = await get_oauth_user_info(provider, access_token, id_token)
    if refresh_token:
        user_info.refresh_token = refresh_token

    # Find or create user
    user = await find_or_create_oauth_user(db, user_info)

    # Create access token and session
    app_access_token = create_access_token({"sub": str(user.id)})
    session_token = await create_session(db, user.id)

    # Build redirect to frontend with token
    redirect_url = f"{settings.oauth_redirect_base_url}/oauth/callback?token={app_access_token}&state={state}"

    redirect = RedirectResponse(url=redirect_url, status_code=302)
    _set_session_cookie(redirect, session_token)
    return redirect
