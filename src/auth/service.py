"""Auth service — business logic for authentication."""

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
import structlog
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Session, User
from src.auth.schemas import RegisterRequest, UserProfile
from src.config import get_settings
from src.exceptions import ConflictError, NotFoundError, UnauthorizedError

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


async def delete_user_account(db: AsyncSession, user_id: UUID) -> None:
    """Soft-delete a user account and all associated data."""
    user = await get_user_by_id(db, user_id)
    user.soft_delete()
    await db.flush()
    logger.info("user_account_deleted", user_id=str(user_id))


def user_to_profile(user: User) -> UserProfile:
    """Convert User model to UserProfile schema."""
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        account_type=user.account_type,
        email_verified=user.email_verified,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at,
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


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    """Reset a user's password using a reset token."""
    user_id = verify_reset_token(token)
    user = await get_user_by_id(db, user_id)

    user.password_hash = hash_password(new_password)
    await db.flush()
    await db.refresh(user)

    logger.info("password_reset_completed", user_id=str(user_id))
    return user
