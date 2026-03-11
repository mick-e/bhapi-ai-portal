"""Portal BFF API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id as _resolve_group_id
from src.groups.privacy import get_child_dashboard
from src.portal.schemas import DashboardResponse, GroupSettingsResponse, UpdateGroupSettingsRequest
from src.portal.service import get_dashboard, get_group_settings, update_group_settings
from src.schemas import GroupContext

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get primary dashboard data (FR-010)."""
    return await get_dashboard(db, _resolve_group_id(group_id, auth), auth.user_id)


@router.get("/settings", response_model=GroupSettingsResponse)
async def get_settings(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get group settings."""
    return await get_group_settings(db, _resolve_group_id(group_id, auth), auth.user_id)


@router.patch("/settings", response_model=GroupSettingsResponse)
async def patch_settings(
    data: UpdateGroupSettingsRequest,
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update group settings."""
    return await update_group_settings(db, _resolve_group_id(group_id, auth), auth.user_id, data)


@router.get("/child-dashboard")
async def child_dashboard(
    member_id: UUID = Query(..., description="The member (child) ID"),
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get child's own filtered dashboard view."""
    return await get_child_dashboard(db, _resolve_group_id(group_id, auth), member_id)
