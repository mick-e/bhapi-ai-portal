"""Auth API endpoints."""

import secrets
import time
from uuid import UUID

import structlog
from fastapi import APIRouter, Body, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
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
    AcceptInviteRequest,
    AcceptInviteResponse,
    ApiKeyResponse,
    ApproveChildRequest,
    ApproveChildResponse,
    AuthResponse,
    ContactInquiryRequest,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    GenerateInviteCodeRequest,
    GenerateInviteCodeResponse,
    LoginRequest,
    OAuthAuthorizeResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RequestParentApprovalRequest,
    RequestParentApprovalResponse,
    UpdateProfileRequest,
    UserProfile,
)
from src.auth.service import (
    approve_child_account,
    authenticate_user,
    confirm_email,
    create_api_key,
    create_session,
    delete_user_account,
    generate_invite_code,
    get_user_by_id,
    list_api_keys,
    redeem_invite_code,
    register_user,
    request_password_reset,
    reset_password,
    revoke_api_key,
    send_parent_approval,
    send_verification_email,
    user_to_profile,
)
from src.config import get_settings
from src.constants import SESSION_COOKIE_NAME
from src.database import get_db
from src.exceptions import ForbiddenError, UnauthorizedError, ValidationError
from src.middleware import endpoint_rate_limit
from src.schemas import GroupContext

settings = get_settings()
logger = structlog.get_logger()
router = APIRouter()

# ---------------------------------------------------------------------------
# OAuth CSRF state store (state -> expiry timestamp)
# ---------------------------------------------------------------------------
_OAUTH_STATE_TTL = 600  # 10 minutes

# In-memory fallback for OAuth auth codes (test-only; production uses Redis)
_oauth_code_store: dict[str, str] = {}
_OAUTH_STATE_MAX_ENTRIES = 10_000

_oauth_states: dict[str, float] = {}


def _evict_expired_oauth_states() -> None:
    """Remove expired entries from the OAuth state store."""
    now = time.time()
    expired = [s for s, exp in _oauth_states.items() if exp <= now]
    for s in expired:
        _oauth_states.pop(s, None)


def _generate_oauth_state() -> str:
    """Generate a cryptographic random state, store it, and return it."""
    _evict_expired_oauth_states()
    # Cap store size to prevent memory exhaustion
    if len(_oauth_states) >= _OAUTH_STATE_MAX_ENTRIES:
        sorted_states = sorted(_oauth_states.items(), key=lambda x: x[1])
        for s, _ in sorted_states[: len(sorted_states) // 2]:
            _oauth_states.pop(s, None)
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time() + _OAUTH_STATE_TTL
    return state


def _validate_oauth_state(state: str) -> None:
    """Validate and consume an OAuth state token (one-time use).

    Raises ForbiddenError if state is missing, unknown, or expired.
    """
    if not state:
        raise ForbiddenError("OAuth state parameter is missing")
    expiry = _oauth_states.pop(state, None)
    if expiry is None:
        raise ForbiddenError("Invalid or already-used OAuth state parameter")
    if time.time() > expiry:
        raise ForbiddenError("OAuth state parameter has expired")


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
    """Create session token (used as both access token and cookie) and return AuthResponse."""
    session_token = await create_session(db, UUID(user_id))
    _set_session_cookie(response, session_token)
    access_token = session_token

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
async def register(
    data: RegisterRequest, request: Request, response: Response,
    db: AsyncSession = Depends(get_db), _rl=Depends(endpoint_rate_limit(5, 3600)),
):
    """Register a new user account, auto-create group, and return token."""
    if not data.privacy_notice_accepted:
        raise ValidationError(
            "You must accept the privacy notice before creating an account. "
            "Please review our privacy policy and check the acceptance box."
        )

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
        logger.debug("verification_email_skipped")  # Details logged in send_verification_email

    # Log privacy notice acceptance for COPPA compliance (non-blocking)
    try:
        from src.compliance.audit_logger import log_audit_event
        async with db.begin_nested():
            await log_audit_event(
                db=db,
                actor_id=user.id,
                action="privacy_notice_accepted",
                resource_type="user",
                resource_id=str(user.id),
                details={
                    "account_type": data.account_type,
                    "ip_address": request.client.host if request.client else None,
                },
            )
    except Exception as exc:
        # Audit logging should never block registration
        logger.debug(
            "auth_registration_audit_degraded",
            error=str(exc),
            email=data.email,
            user_id=str(user.id),
        )

    auth_response = await _create_auth_response(db, str(user.id), response)
    # UK AADC re-review (Phase 4 Task 24): users registering from GB get a
    # follow-up consent flow. Frontend reads requires_aadc_consent and shows
    # the AADC consent screen before unlocking the dashboard.
    if data.country_code and data.country_code.upper() == "GB":
        auth_response.requires_aadc_consent = True
    return auth_response


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest, response: Response,
    db: AsyncSession = Depends(get_db), _rl=Depends(endpoint_rate_limit(10, 3600)),
):
    """Login with email and password."""
    user = await authenticate_user(db, data.email, data.password)

    return await _create_auth_response(db, str(user.id), response)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Logout and invalidate session."""
    from src.auth.service import invalidate_session

    # Invalidate session from Bearer header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        await invalidate_session(db, auth_header[7:])

    # Invalidate session from cookie
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if session_cookie:
        await invalidate_session(db, session_cookie)

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


_PATCH_ME_ALLOWED_FIELDS = {"display_name", "email", "locale", "timezone"}


@router.patch("/me", response_model=UserProfile)
async def update_me(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Update current user profile.

    Only whitelisted fields are applied. Sensitive fields like email_verified,
    mfa_enabled, role, is_admin, and password_hash are explicitly rejected to
    prevent mass-assignment attacks (Finding #5).
    """
    user = await get_user_by_id(db, auth.user_id)

    # Explicit whitelist — only safe fields may be updated
    updates = data.model_dump(exclude_unset=True)
    for field in list(updates.keys()):
        if field not in _PATCH_ME_ALLOWED_FIELDS:
            updates.pop(field)

    for field, value in updates.items():
        if value is not None:
            setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return user_to_profile(user, group_id=auth.group_id, role=auth.role)


@router.post("/password/reset", status_code=202)
async def request_reset(
    data: PasswordResetRequest, db: AsyncSession = Depends(get_db),
    _rl=Depends(endpoint_rate_limit(5, 3600)),
):
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

    authorization_url, _provider_state = get_authorization_url(provider)

    # Generate and store a CSRF-safe state token (server-side validation)
    state = _generate_oauth_state()

    # Replace the provider-generated state in the URL with our validated one
    authorization_url = authorization_url.replace(f"state={_provider_state}", f"state={state}")

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

    # Validate CSRF state parameter (one-time use)
    _validate_oauth_state(state)

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

    # Create session token (used for both Bearer and cookie auth)
    session_token = await create_session(db, user.id)

    # Generate short-lived auth code (60s TTL) instead of leaking session token in URL.
    # The frontend exchanges this code for the real session via POST /oauth/exchange.
    auth_code = secrets.token_urlsafe(32)
    from src.redis_client import get_redis

    redis = get_redis()
    if redis is None:
        # Tests-only fallback: use in-memory dict
        _oauth_code_store[auth_code] = session_token
    else:
        await redis.set(f"bhapi:oauth_code:{auth_code}", session_token, ex=60)

    redirect_url = f"{settings.oauth_redirect_base_url}/oauth/callback?code={auth_code}&state={state}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/oauth/exchange")
async def exchange_oauth_code(
    code: str = Body(..., embed=True),
    response: Response = None,
):
    """Exchange a one-time short-lived OAuth auth code for a session token.

    The auth code is generated by the OAuth callback and has a 60-second TTL.
    It can only be used once — a second exchange with the same code returns 401.
    """
    from src.redis_client import get_redis

    redis = get_redis()
    key = f"bhapi:oauth_code:{code}"

    if redis is None:
        session_token = _oauth_code_store.pop(code, None)
    else:
        session_token = await redis.get(key)
        if session_token:
            await redis.delete(key)  # one-time use

    if not session_token:
        raise UnauthorizedError("Invalid or expired authorization code")

    payload = JSONResponse({"token": session_token})
    _set_session_cookie(payload, session_token)
    return payload


# ---------------------------------------------------------------------------
# Cross-app onboarding (P3-L5)
# ---------------------------------------------------------------------------


@router.post("/invite-child", response_model=GenerateInviteCodeResponse, status_code=201)
async def invite_child(
    data: GenerateInviteCodeRequest,
    db: AsyncSession = Depends(get_db),
    auth: "GroupContext" = Depends(get_current_user),
):
    """Parent generates a 6-char alphanumeric invite code for a child to join their group.

    The code expires in 48 hours. Requires an authenticated parent session.
    """
    invite = await generate_invite_code(db, data.group_id, auth.user_id)
    return GenerateInviteCodeResponse(
        code=invite.code,
        group_id=invite.group_id,
        expires_at=invite.expires_at,
    )


@router.post("/accept-invite", response_model=AcceptInviteResponse, status_code=200)
async def accept_invite(
    data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Child redeems an invite code to join a family group.

    Public endpoint — child may not have a session yet when entering the code.
    Returns the group and member IDs once linked.
    """
    group_id, member_id = await redeem_invite_code(db, data.code, data.child_user_id)
    return AcceptInviteResponse(group_id=group_id, member_id=member_id)


@router.post("/request-parent-approval", response_model=RequestParentApprovalResponse, status_code=201)
async def request_parent_approval(
    data: RequestParentApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Child submits a parent e-mail to trigger the approval flow.

    Public endpoint. Creates a pending approval and e-mails the parent an
    approval link (best-effort — failure does not block the response).
    """
    approval = await send_parent_approval(db, data.child_id, data.parent_email)
    return RequestParentApprovalResponse(
        request_id=approval.id,
        status=approval.status,
    )


@router.post("/approve-child", response_model=ApproveChildResponse, status_code=200)
async def approve_child(
    data: ApproveChildRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parent approves a child account using the single-use token from the approval email.

    Public endpoint — parent clicks the link in their email and lands on the
    web approval page which calls this endpoint. Links the child to the
    parent's group and marks the request approved.
    """
    child_id, group_id = await approve_child_account(db, data.token)
    return ApproveChildResponse(child_id=child_id, group_id=group_id)
