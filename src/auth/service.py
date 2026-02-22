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
from src.auth.schemas import RegisterRequest, TokenResponse, UserProfile
from src.config import get_settings
from src.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError

logger = structlog.get_logger()
settings = get_settings()


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
