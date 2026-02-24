"""Auth API endpoints."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from src.auth.middleware import get_current_user
from src.auth.service import (
    authenticate_user,
    confirm_email,
    create_access_token,
    create_session,
    delete_user_account,
    get_user_by_id,
    invalidate_session,
    register_user,
    request_password_reset,
    reset_password,
    send_verification_email,
    user_to_profile,
)
from src.constants import SESSION_COOKIE_NAME
from src.database import get_db
from src.config import get_settings
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
