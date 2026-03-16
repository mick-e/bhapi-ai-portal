"""Auth dependency for endpoint-level authentication."""

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import API_KEY_PREFIX, decode_token
from src.constants import SESSION_COOKIE_NAME
from src.database import get_db
from src.exceptions import UnauthorizedError
from src.schemas import GroupContext


async def _authenticate_api_key(
    db: AsyncSession, raw_key: str,
) -> GroupContext:
    """Validate a bhapi_sk_ API key and return the associated GroupContext."""
    from src.auth.models import ApiKey, User
    from src.groups.models import GroupMember

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise UnauthorizedError("Invalid or revoked API key")

    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    # Fetch user + group context
    row = (
        await db.execute(
            select(User.id, GroupMember.group_id, GroupMember.role)
            .outerjoin(GroupMember, GroupMember.user_id == User.id)
            .where(User.id == api_key.user_id)
            .limit(1)
        )
    ).first()
    if not row:
        raise UnauthorizedError("User account not found")

    return GroupContext(user_id=row[0], group_id=row[1], role=row[2])


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GroupContext:
    """Extract and validate user identity from API key, JWT bearer, or session cookie.

    Returns a GroupContext with the authenticated user's ID.
    Verifies the user still exists in the database and the session is valid.
    """
    user_id: str | None = None
    raw_token: str | None = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]

        # API key authentication (bhapi_sk_ prefix) — no expiry
        if raw_token.startswith(API_KEY_PREFIX):
            return await _authenticate_api_key(db, raw_token)

        # JWT token authentication
        payload = decode_token(raw_token)
        if payload.get("type") != "session":
            raise UnauthorizedError("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token: missing subject")
    else:
        # Try session cookie
        session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if session_cookie:
            raw_token = session_cookie
            payload = decode_token(session_cookie)
            if payload.get("type") != "session":
                raise UnauthorizedError("Invalid session token")
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedError("Invalid session token: missing subject")

    if not user_id:
        raise UnauthorizedError("Authentication required")

    # Validate token against session table (ensures logout/password-change invalidation)
    if raw_token:
        from src.auth.models import Session

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        session_result = await db.execute(
            select(Session).where(
                Session.token_hash == token_hash,
                Session.expires_at > datetime.now(timezone.utc),
            )
        )
        if not session_result.scalar_one_or_none():
            raise UnauthorizedError("Session expired or invalidated")

    # Verify user exists and fetch primary group in a single query.
    uid = UUID(user_id)

    from src.auth.models import User
    from src.groups.models import GroupMember

    result = await db.execute(
        select(User.id, GroupMember.group_id, GroupMember.role)
        .outerjoin(GroupMember, GroupMember.user_id == User.id)
        .where(User.id == uid)
        .limit(1)
    )
    row = result.first()
    if not row:
        raise UnauthorizedError("User account not found")

    return GroupContext(user_id=uid, group_id=row.group_id, role=row.role)
