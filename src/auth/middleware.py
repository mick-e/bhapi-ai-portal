"""Auth dependency for endpoint-level authentication."""

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import decode_token
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

    # Verify user exists and fetch primary group in a single query.
    # Uses a LEFT JOIN so we get the user row even if they have no groups.
    uid = UUID(user_id)

    from sqlalchemy import select
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
