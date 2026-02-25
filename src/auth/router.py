"""Auth API endpoints."""

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
    create_session,
    delete_user_account,
    get_user_by_id,
    register_user,
    request_password_reset,
    reset_password,
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


@router.post("/register", response_model=UserProfile, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user = await register_user(db, data)

    # Send verification email (non-blocking — don't fail registration on email error)
    try:
        await send_verification_email(user)
    except Exception:
        pass  # Logged in send_verification_email

    return user_to_profile(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    user = await authenticate_user(db, data.email, data.password)

    # Create access token
    access_token = create_access_token({"sub": str(user.id)})

    # Create session cookie
    session_token = await create_session(db, user.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_timeout_hours * 3600,
        domain=settings.cookie_domain,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


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
    """Get current user profile."""
    user = await get_user_by_id(db, auth.user_id)
    return user_to_profile(user)


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
    redirect.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_timeout_hours * 3600,
        domain=settings.cookie_domain,
    )
    return redirect
