"""FastAPI dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.exceptions import ValidationError
from src.schemas import GroupContext, PaginationParams

# Type aliases for clean endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]


async def require_active_trial_or_subscription(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupContext:
    """Enforce active trial or paid subscription.

    Raise TrialExpiredError if the group's free trial has expired
    and no paid subscription exists.
    """
    from src.billing.trial import get_trial_status
    from src.exceptions import TrialExpiredError

    gid = auth.group_id
    if not gid:
        return auth

    status = await get_trial_status(db, gid)
    if status.is_locked:
        raise TrialExpiredError()

    return auth


def resolve_group_id(group_id: UUID | None, auth: GroupContext) -> UUID:
    """Resolve group_id from explicit param or the user's primary group."""
    gid = group_id or auth.group_id
    if not gid:
        raise ValidationError("No group found. Please create a group first.")
    return gid


async def resolve_group_id_verified(
    group_id: UUID | None, auth: GroupContext, db: AsyncSession,
) -> UUID:
    """Resolve group_id and verify the user is a member of that group.

    Use for sensitive endpoints (billing, integrations, etc.) where
    cross-group access must be prevented.
    """
    from src.exceptions import ForbiddenError
    from src.groups.models import GroupMember

    gid = group_id or auth.group_id
    if not gid:
        raise ValidationError("No group found. Please create a group first.")
    # If a specific group_id was provided, verify DB membership
    if group_id is not None and group_id != auth.group_id:
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == auth.user_id,
            )
        )
        if not result.scalar_one_or_none():
            raise ForbiddenError("You do not have access to this group")
    return gid
