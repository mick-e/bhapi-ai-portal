"""Age tier API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import AgeTier, check_permission as check_perm
from src.age_tier.schemas import (
    AgeTierConfigCreate,
    AgeTierConfigResponse,
    PermissionCheckResponse,
)
from src.age_tier.service import (
    assign_tier,
    get_member_permissions,
    get_member_tier,
)
from src.auth.middleware import get_current_user
from src.database import get_db
from src.age_tier.rules import get_permissions
from src.schemas import GroupContext

router = APIRouter()


@router.post("/assign", response_model=AgeTierConfigResponse)
async def assign_age_tier(
    data: AgeTierConfigCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign or update the age tier for a group member."""
    config = await assign_tier(db, data, auth=auth)
    tier = AgeTier(config.tier)
    perms = get_permissions(
        tier,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
    return AgeTierConfigResponse(
        id=config.id,
        member_id=config.member_id,
        tier=config.tier,
        date_of_birth=config.date_of_birth,
        jurisdiction=config.jurisdiction,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
        permissions=perms,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/member/{member_id}", response_model=AgeTierConfigResponse)
async def get_member_age_tier(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the age tier configuration for a member."""
    config = await get_member_tier(db, member_id, auth=auth)
    tier = AgeTier(config.tier)
    perms = get_permissions(
        tier,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
    return AgeTierConfigResponse(
        id=config.id,
        member_id=config.member_id,
        tier=config.tier,
        date_of_birth=config.date_of_birth,
        jurisdiction=config.jurisdiction,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
        permissions=perms,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/member/{member_id}/permissions")
async def get_permissions_endpoint(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the effective permissions for a member."""
    perms = await get_member_permissions(db, member_id, auth=auth)
    return {"member_id": str(member_id), "permissions": perms}


@router.get(
    "/member/{member_id}/check/{permission}",
    response_model=PermissionCheckResponse,
)
async def check_permission_endpoint(
    member_id: UUID,
    permission: str,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether a specific permission is allowed for a member."""
    config = await get_member_tier(db, member_id, auth=auth)
    tier = AgeTier(config.tier)
    allowed = check_perm(
        tier,
        permission,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
    return PermissionCheckResponse(
        member_id=member_id,
        permission=permission,
        allowed=allowed,
        tier=config.tier,
    )
