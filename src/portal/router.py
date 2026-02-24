"""Portal BFF API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.portal.schemas import DashboardResponse, GroupSettingsResponse, UpdateGroupSettingsRequest
from src.portal.service import get_dashboard, get_group_settings, update_group_settings
from src.schemas import GroupContext

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    group_id: UUID = Query(..., description="Group ID to get dashboard for"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get primary dashboard data (FR-010)."""
    return await get_dashboard(db, group_id, auth.user_id)


@router.get("/settings", response_model=GroupSettingsResponse)
async def get_settings(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get group settings."""
    return await get_group_settings(db, group_id, auth.user_id)


@router.patch("/settings", response_model=GroupSettingsResponse)
async def patch_settings(
    data: UpdateGroupSettingsRequest,
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update group settings."""
    return await update_group_settings(db, group_id, auth.user_id, data)
