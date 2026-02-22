"""Groups API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.groups.schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    InvitationCreate,
    InvitationResponse,
    MemberAdd,
    MemberResponse,
    RoleChange,
)
from src.groups.service import (
    accept_invitation,
    add_member,
    change_member_role,
    create_group,
    create_invitation,
    delete_group,
    get_group,
    group_to_response,
    list_members,
    list_user_groups,
    remove_member,
    update_group,
)
from src.schemas import GroupContext

router = APIRouter()


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group_endpoint(
    data: GroupCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new group (FR-003)."""
    group = await create_group(db, auth.user_id, data)
    return group_to_response(group)


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all groups the user belongs to."""
    groups = await list_user_groups(db, auth.user_id)
    return [group_to_response(g) for g in groups]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group_endpoint(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get group details."""
    group = await get_group(db, group_id, auth.user_id)
    return group_to_response(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group_endpoint(
    group_id: UUID,
    data: GroupUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update group settings."""
    group = await update_group(db, group_id, auth.user_id, name=data.name, settings=data.settings)
    return group_to_response(group)


@router.delete("/{group_id}", status_code=204)
async def delete_group_endpoint(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a group (soft delete)."""
    await delete_group(db, group_id, auth.user_id)
    return None


@router.post("/{group_id}/members", response_model=MemberResponse, status_code=201)
async def add_member_endpoint(
    group_id: UUID,
    data: MemberAdd,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to the group."""
    member = await add_member(db, group_id, auth.user_id, data)
    return member


@router.get("/{group_id}/members", response_model=list[MemberResponse])
async def list_members_endpoint(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List group members (FR-012)."""
    members = await list_members(db, group_id, auth.user_id)
    return members


@router.delete("/{group_id}/members/{member_id}", status_code=204)
async def remove_member_endpoint(
    group_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the group."""
    await remove_member(db, group_id, member_id, auth.user_id)
    return None


@router.patch("/{group_id}/members/{member_id}/role", response_model=MemberResponse)
async def change_role_endpoint(
    group_id: UUID,
    member_id: UUID,
    data: RoleChange,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a member's role (FR-005)."""
    member = await change_member_role(db, group_id, member_id, auth.user_id, data.role)
    return member


@router.post("/{group_id}/invite", response_model=InvitationResponse, status_code=201)
async def invite_member(
    group_id: UUID,
    data: InvitationCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a member to the group (FR-003, FR-004)."""
    invitation = await create_invitation(db, group_id, auth.user_id, data)
    return invitation


@router.post("/invitations/{token}/accept", response_model=MemberResponse, status_code=201)
async def accept_invitation_endpoint(
    token: str,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a group invitation (FR-004)."""
    member = await accept_invitation(db, token, auth.user_id)
    return member
