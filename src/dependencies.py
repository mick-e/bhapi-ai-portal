"""FastAPI dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import ValidationError
from src.schemas import GroupContext, PaginationParams

# Type aliases for clean endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]


def resolve_group_id(group_id: UUID | None, auth: GroupContext) -> UUID:
    """Resolve group_id from explicit param or the user's primary group."""
    gid = group_id or auth.group_id
    if not gid:
        raise ValidationError("No group found. Please create a group first.")
    return gid
