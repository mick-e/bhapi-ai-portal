"""Auth service — business logic for authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
import structlog
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import ApiKey, ChildInviteCode, ParentApprovalRequest, Session, User
from src.auth.schemas import RegisterRequest, UserProfile
from src.config import get_settings
from src.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError

logger = structlog.get_logger()
settings = get_settings()

# Rate limit tracking for password reset: {email: [timestamps]}
_reset_rate_tracker: dict[str, list[float]] = {}
_RESET_RATE_LIMIT = 5
_RESET_RATE_WINDOW = 3600  # 1 hour


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    to_encode.setdefault("type", "access")
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(timezone.utc)
    to_encode.setdefault("jti", str(uuid4()))
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.JWTError:
        raise UnauthorizedError("Invalid token")


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Register a new user."""
    # Check for existing user
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError(f"User with email '{data.email}' already exists")

    user = User(
        id=uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        account_type=data.account_type,
        date_of_birth=data.date_of_birth,
        email_verified=False,
        mfa_enabled=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("user_registered", user_id=str(user.id), account_type=data.account_type)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Authenticate a user by email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise UnauthorizedError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    return user


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User", str(user_id))
    return user


async def create_session(db: AsyncSession, user_id: UUID, device_info: dict | None = None) -> str:
    """Create a session and return session token."""
    token_data = {
        "sub": str(user_id),
        "type": "session",
    }
    session_token = create_access_token(
        token_data,
        expires_delta=timedelta(hours=settings.session_timeout_hours),
    )

    token_hash = hashlib.sha256(session_token.encode()).hexdigest()

    session = Session(
        id=uuid4(),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_timeout_hours),
        device_info=device_info,
    )
    db.add(session)
    await db.flush()

    return session_token


async def invalidate_session(db: AsyncSession, token: str) -> None:
    """Invalidate a session by token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(select(Session).where(Session.token_hash == token_hash))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.flush()


async def invalidate_all_sessions(db: AsyncSession, user_id: UUID) -> None:
    """Invalidate all sessions for a user (e.g. after password change)."""
    result = await db.execute(select(Session).where(Session.user_id == user_id))
    sessions = result.scalars().all()
    for s in sessions:
        await db.delete(s)
    if sessions:
        await db.flush()


async def delete_user_account(db: AsyncSession, user_id: UUID) -> None:
    """Soft-delete a user account and all associated data."""
    user = await get_user_by_id(db, user_id)
    user.soft_delete()
    await db.flush()
    logger.info("user_account_deleted", user_id=str(user_id))


def user_to_profile(
    user: User,
    group_id: "UUID | None" = None,
    role: str | None = None,
) -> UserProfile:
    """Convert User model to UserProfile schema with optional group context."""
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        account_type=user.account_type,
        group_id=group_id,
        role=role,
        email_verified=user.email_verified,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
        updated_at=getattr(user, "updated_at", None),
    )


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def create_email_verification_token(user_id: UUID) -> str:
    """Create a JWT token for email verification (24h expiry)."""
    return create_access_token(
        {"sub": str(user_id), "type": "email_verification"},
        expires_delta=timedelta(hours=24),
    )


def verify_email_token(token: str) -> UUID:
    """Decode an email verification token. Returns user_id.

    Raises UnauthorizedError if token is invalid or expired.
    """
    payload = decode_token(token)
    if payload.get("type") != "email_verification":
        raise UnauthorizedError("Invalid verification token")
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid verification token")


async def confirm_email(db: AsyncSession, token: str) -> User:
    """Verify a user's email address using a verification token."""
    user_id = verify_email_token(token)
    user = await get_user_by_id(db, user_id)
    if user.email_verified:
        return user  # Already verified, no-op

    user.email_verified = True
    await db.flush()
    await db.refresh(user)

    logger.info("email_verified", user_id=str(user_id))
    return user


async def send_verification_email(user: User) -> bool:
    """Send an email verification link to a user."""
    from src.email import templates
    from src.email.service import send_email

    token = create_email_verification_token(user.id)
    verification_url = f"https://bhapi.ai/verify-email?token={token}"

    subject, html, plain = templates.email_verification(
        display_name=user.display_name,
        verification_url=verification_url,
    )

    return await send_email(
        to_email=user.email,
        subject=subject,
        html_content=html,
        plain_content=plain,
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

def _check_reset_rate_limit(email: str) -> bool:
    """Check if email has exceeded reset rate limit (5/hour). Returns True if OK."""
    import time
    now = time.time()

    if email not in _reset_rate_tracker:
        _reset_rate_tracker[email] = []

    # Prune old entries
    _reset_rate_tracker[email] = [
        t for t in _reset_rate_tracker[email] if now - t < _RESET_RATE_WINDOW
    ]

    if len(_reset_rate_tracker[email]) >= _RESET_RATE_LIMIT:
        return False

    _reset_rate_tracker[email].append(now)
    return True


def create_password_reset_token(user_id: UUID) -> str:
    """Create a JWT token for password reset (1h expiry)."""
    return create_access_token(
        {"sub": str(user_id), "type": "password_reset"},
        expires_delta=timedelta(hours=1),
    )


def verify_reset_token(token: str) -> UUID:
    """Decode a password reset token. Returns user_id.

    Raises UnauthorizedError if token is invalid or expired.
    """
    payload = decode_token(token)
    if payload.get("type") != "password_reset":
        raise UnauthorizedError("Invalid reset token")
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid reset token")


async def request_password_reset(db: AsyncSession, email: str) -> bool:
    """Process a password reset request.

    Always returns True to prevent email enumeration.
    Only sends email if user exists and rate limit not exceeded.
    """
    if not _check_reset_rate_limit(email):
        logger.warning("password_reset_rate_limited", email=email)
        return True  # Don't reveal rate limiting

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        logger.debug("password_reset_no_user", email=email)
        return True  # Don't reveal if user exists

    await send_reset_email(user)
    return True


async def send_reset_email(user: User) -> bool:
    """Send a password reset email."""
    from src.email import templates
    from src.email.service import send_email

    token = create_password_reset_token(user.id)
    reset_url = f"https://bhapi.ai/reset-password?token={token}"

    subject, html, plain = templates.password_reset(
        display_name=user.display_name,
        reset_url=reset_url,
    )

    return await send_email(
        to_email=user.email,
        subject=subject,
        html_content=html,
        plain_content=plain,
    )


_used_reset_tokens: set[str] = set()


async def try_sso_auto_provision(db: AsyncSession, user: User) -> None:
    """Check if user's email domain matches an SSO config and auto-provision.

    Called after OAuth login to automatically add the user as a group member
    when the group has SSO auto-provisioning enabled for the user's domain.
    """
    domain = user.email.split("@")[-1] if "@" in user.email else None
    if not domain:
        return

    from sqlalchemy import select

    from src.integrations.sso_models import SSOConfig

    # Find SSO configs where the tenant_id matches the user's email domain
    result = await db.execute(
        select(SSOConfig).where(
            SSOConfig.tenant_id == domain,
            SSOConfig.auto_provision_members.is_(True),
        )
    )
    sso_configs = list(result.scalars().all())

    if not sso_configs:
        return

    from src.integrations.sso_provisioner import auto_provision_member

    for sso_config in sso_configs:
        try:
            await auto_provision_member(
                db=db,
                group_id=sso_config.group_id,
                sso_user_info={
                    "email": user.email,
                    "display_name": user.display_name,
                    "external_id": str(user.id),
                },
            )
        except Exception as exc:
            logger.error(
                "sso_auto_provision_failed",
                user_id=str(user.id),
                sso_config_id=str(sso_config.id),
                error=str(exc),
            )


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    """Reset a user's password using a reset token."""
    # Check if this token has already been used
    payload = decode_token(token)
    jti = payload.get("jti")
    if jti and jti in _used_reset_tokens:
        raise UnauthorizedError("Reset token already used")

    user_id = verify_reset_token(token)
    user = await get_user_by_id(db, user_id)

    user.password_hash = hash_password(new_password)

    # Mark token as used
    if jti:
        _used_reset_tokens.add(jti)

    # Invalidate all existing sessions for this user
    await invalidate_all_sessions(db, user_id)

    await db.flush()
    await db.refresh(user)

    logger.info("password_reset_completed", user_id=str(user_id))
    return user


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

API_KEY_PREFIX = "bhapi_sk_"


def _generate_raw_key() -> str:
    """Generate a cryptographically secure API key string."""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def _hash_api_key(raw_key: str) -> str:
    """Hash an API key for storage using SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _key_preview(raw_key: str) -> str:
    """Create a preview like 'bhapi_sk_Ab...3f2a'."""
    return raw_key[:12] + "..." + raw_key[-4:]


async def list_api_keys(db: AsyncSession, user_id: UUID) -> list[ApiKey]:
    """List all non-revoked API keys for a user."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def create_api_key(
    db: AsyncSession,
    user_id: UUID,
    group_id: UUID,
    name: str | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (model, full_key_string)."""
    raw_key = _generate_raw_key()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,
        group_id=group_id,
        name=name,
        key_hash=_hash_api_key(raw_key),
        key_prefix=_key_preview(raw_key),
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    logger.info("api_key_created", key_id=str(api_key.id), user_id=str(user_id))
    return api_key, raw_key


async def revoke_api_key(db: AsyncSession, key_id: UUID, user_id: UUID) -> ApiKey:
    """Revoke an API key by setting revoked_at."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise NotFoundError("API Key", str(key_id))
    if api_key.revoked_at:
        raise ConflictError("API key is already revoked")

    api_key.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(api_key)

    logger.info("api_key_revoked", key_id=str(key_id), user_id=str(user_id))
    return api_key


# ---------------------------------------------------------------------------
# Cross-app onboarding (P3-L5)
# ---------------------------------------------------------------------------

# In-memory rate limit for invite code generation: {user_id_str: [timestamps]}
_invite_rate_tracker: dict[str, list[float]] = {}
_INVITE_RATE_LIMIT = 10  # per hour
_INVITE_RATE_WINDOW = 3600

# Single-use approval token tracking (mirrors _used_reset_tokens pattern)
_used_approval_tokens: set[str] = set()


def _check_invite_rate_limit(user_id: UUID) -> bool:
    """Return True if the user may generate another invite code. False = rate limited."""
    import time
    now = time.time()
    key = str(user_id)
    if key not in _invite_rate_tracker:
        _invite_rate_tracker[key] = []

    _invite_rate_tracker[key] = [
        t for t in _invite_rate_tracker[key] if now - t < _INVITE_RATE_WINDOW
    ]
    if len(_invite_rate_tracker[key]) >= _INVITE_RATE_LIMIT:
        return False

    _invite_rate_tracker[key].append(now)
    return True


async def generate_invite_code(
    db: AsyncSession,
    group_id: UUID,
    parent_id: UUID,
) -> ChildInviteCode:
    """Create a 6-char uppercase alphanumeric invite code for a family group.

    The code expires in 48 hours. Any previously unused codes for the same
    parent + group are left intact (they expire naturally).
    """
    from src.exceptions import RateLimitError

    if not _check_invite_rate_limit(parent_id):
        raise RateLimitError("Too many invite codes generated. Please wait before generating another.")

    # Generate collision-resistant 6-char code
    code = secrets.token_hex(3).upper()[:6]

    # Very unlikely, but re-roll on collision (skip DB-level timezone filter for SQLite compat)
    for _ in range(5):
        existing = await db.execute(
            select(ChildInviteCode).where(
                ChildInviteCode.code == code,
                ChildInviteCode.used_at.is_(None),
            )
        )
        row = existing.scalar_one_or_none()
        if not row:
            break
        # Accept if existing row is expired (it will be overwritten by new one)
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            break
        code = secrets.token_hex(3).upper()[:6]

    invite = ChildInviteCode(
        id=uuid4(),
        code=code,
        group_id=group_id,
        created_by=parent_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    logger.info(
        "invite_code_generated",
        group_id=str(group_id),
        parent_id=str(parent_id),
        code=code,
    )
    return invite


async def redeem_invite_code(
    db: AsyncSession,
    code: str,
    child_user_id: UUID,
) -> tuple[UUID, UUID]:
    """Validate and redeem an invite code, linking the child to the family group.

    Returns (group_id, member_id).
    Raises NotFoundError if code not found, ValidationError if expired/used.
    """
    result = await db.execute(
        select(ChildInviteCode).where(ChildInviteCode.code == code.upper())
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise NotFoundError("Invite code", code)

    if invite.used_at is not None:
        raise ValidationError("Invite code has already been used")

    # SQLite returns naive datetimes; normalise for comparison
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise ValidationError("Invite code has expired")

    # Fetch child user to get their info for the membership record
    child = await get_user_by_id(db, child_user_id)

    # Mark code used
    invite.used_at = datetime.now(timezone.utc)

    # Add child as a group member
    from src.groups.models import GroupMember

    member = GroupMember(
        id=uuid4(),
        group_id=invite.group_id,
        user_id=child_user_id,
        role="member",
        display_name=child.display_name,
        date_of_birth=child.date_of_birth,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    # Assign age tier if DOB available
    if child.date_of_birth:
        try:
            from src.age_tier.service import assign_age_tier
            await assign_age_tier(db, child_user_id, invite.group_id)
        except Exception:
            pass  # Non-blocking — age tier assignment is best-effort

    logger.info(
        "invite_code_redeemed",
        code=code.upper(),
        child_user_id=str(child_user_id),
        group_id=str(invite.group_id),
        member_id=str(member.id),
    )
    return invite.group_id, member.id


async def send_parent_approval(
    db: AsyncSession,
    child_id: UUID,
    parent_email: str,
) -> ParentApprovalRequest:
    """Create a parental approval request and log the email dispatch.

    In production the approval link is sent via SendGrid.  In development/test
    the send is skipped (no API key) and only logged.

    Returns the created ParentApprovalRequest.
    """
    child = await get_user_by_id(db, child_id)

    # Generate a single-use approval token
    raw_token = str(uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    approval = ParentApprovalRequest(
        id=uuid4(),
        child_id=child_id,
        parent_email=parent_email,
        token_hash=token_hash,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(approval)
    await db.flush()
    await db.refresh(approval)

    # Store raw token in a transient attribute so the router can return it
    # without a second query (never persisted).
    approval.__dict__["_raw_token"] = raw_token  # type: ignore[assignment]

    approval_url = f"https://bhapi.ai/approve?token={raw_token}"
    logger.info(
        "parent_approval_email_dispatched",
        child_id=str(child_id),
        parent_email=parent_email,
        approval_id=str(approval.id),
        approval_url=approval_url,
    )

    # Best-effort email send — failure does not block the API response
    try:
        from src.email.service import send_email

        subject = f"Action required: {child.display_name} wants to join Bhapi"
        html_content = (
            f"<h2>Parental Approval Request</h2>"
            f"<p>{child.display_name} has requested to join the Bhapi platform.</p>"
            f"<p>Click the link below to review and approve or deny:</p>"
            f'<p><a href="{approval_url}">Review Request</a></p>'
            f"<p>This link expires in 48 hours.</p>"
        )
        await send_email(
            to_email=parent_email,
            subject=subject,
            html_content=html_content,
        )
    except Exception as exc:
        logger.warning("parent_approval_email_failed", error=str(exc))

    return approval


async def approve_child_account(
    db: AsyncSession,
    token: str,
) -> tuple[UUID, UUID]:
    """Verify an approval token and link the child to the parent's group.

    Returns (child_id, group_id).
    Raises ValidationError if token invalid, expired, or already used.
    """
    # Check single-use
    if token in _used_approval_tokens:
        raise ValidationError("Approval token has already been used")

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    result = await db.execute(
        select(ParentApprovalRequest).where(
            ParentApprovalRequest.token_hash == token_hash
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise NotFoundError("Approval request", "token")

    if approval.status != "pending":
        raise ValidationError(f"Approval request is already {approval.status}")

    approval_expires = approval.expires_at
    if approval_expires.tzinfo is None:
        approval_expires = approval_expires.replace(tzinfo=timezone.utc)
    if approval_expires < datetime.now(timezone.utc):
        raise ValidationError("Approval token has expired")

    # Mark token as used (in-memory guard against replay in same process)
    _used_approval_tokens.add(token)

    # Update approval status
    approval.status = "approved"

    # Find the parent's group — look up by parent_email
    result2 = await db.execute(
        select(User).where(User.email == approval.parent_email)
    )
    parent = result2.scalar_one_or_none()

    from src.groups.models import GroupMember

    group_id: UUID | None = approval.group_id

    if not group_id and parent:
        # Locate parent's primary group membership
        gm_result = await db.execute(
            select(GroupMember).where(
                GroupMember.user_id == parent.id,
                GroupMember.role.in_(["parent", "school_admin", "club_admin"]),
            ).limit(1)
        )
        gm = gm_result.scalar_one_or_none()
        if gm:
            group_id = gm.group_id

    if not group_id:
        raise ValidationError("No parent group found — the parent must have an existing group")

    # Link child to group if not already a member
    existing_member = await db.execute(
        select(GroupMember).where(
            GroupMember.user_id == approval.child_id,
            GroupMember.group_id == group_id,
        )
    )
    existing = existing_member.scalar_one_or_none()

    if not existing:
        child = await get_user_by_id(db, approval.child_id)
        member = GroupMember(
            id=uuid4(),
            group_id=group_id,
            user_id=approval.child_id,
            role="member",
            display_name=child.display_name,
            date_of_birth=child.date_of_birth,
        )
        db.add(member)

    approval.group_id = group_id
    await db.flush()

    logger.info(
        "child_account_approved",
        child_id=str(approval.child_id),
        group_id=str(group_id),
    )
    return approval.child_id, group_id
