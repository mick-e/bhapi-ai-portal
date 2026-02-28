"""Auth dependency for endpoint-level authentication."""

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import decode_token, get_user_by_id
from src.constants import SESSION_COOKIE_NAME
from src.database import get_db
from src.exceptions import UnauthorizedError
from src.schemas import GroupContext


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GroupContext:
    """Extract and validate user identity from JWT bearer or session cookie.

    Returns a GroupContext with the authenticated user's ID.
    Verifies the user still exists in the database.
    """
    user_id: str | None = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token: missing subject")
    else:
        # Try session cookie
        session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
        if session_cookie:
            payload = decode_token(session_cookie)
            if payload.get("type") != "session":
                raise UnauthorizedError("Invalid session token")
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedError("Invalid session token: missing subject")

    if not user_id:
        raise UnauthorizedError("Authentication required")

    # Verify user still exists (handles deleted accounts)
    uid = UUID(user_id)
    try:
        await get_user_by_id(db, uid)
    except Exception:
        raise UnauthorizedError("User account not found")

    # Look up user's primary group
    from src.groups.service import list_user_groups
    groups = await list_user_groups(db, uid)
    group_id = groups[0].id if groups else None
    role = None
    if groups:
        # Get the user's role in their primary group
        from sqlalchemy import select
        from src.groups.models import GroupMember
        result = await db.execute(
            select(GroupMember.role).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == uid,
            )
        )
        role = result.scalar_one_or_none()

    return GroupContext(user_id=uid, group_id=group_id, role=role)
