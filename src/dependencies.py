"""FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas import GroupContext, PaginationParams

# Type aliases for clean endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]


# Auth dependency placeholder — will be implemented in src/auth/middleware.py
async def get_current_user() -> GroupContext:
    """Get authenticated user context. Override in auth module."""
    raise NotImplementedError("Auth middleware not configured")


AuthContext = Annotated[GroupContext, Depends(get_current_user)]
