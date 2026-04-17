"""Groups API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.database import get_db
from src.groups.agreement import FamilyAgreement as _FamilyAgreement  # noqa: F401 — register model
from src.groups.emergency_contacts import EmergencyContact as _EmergencyContact  # noqa: F401 — register model
from src.groups.privacy import (
    disable_child_self_view,
    enable_child_self_view,
    get_child_self_view,
    get_member_visibility,
    set_member_visibility,
)
from src.groups.rewards import (
    check_and_award_rewards,
)
from src.groups.rewards import (
    list_rewards as list_member_rewards,
)
from src.groups.schemas import (
    AgreementCreateRequest,
    AgreementSignRequest,
    AgreementUpdateRequest,
    ChildSelfViewRequest,
    ChildSelfViewResponse,
    ConsentCreate,
    ConsentResponse,
    EmergencyContactCreate,
    EmergencyContactUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    InvitationCreate,
    InvitationResponse,
    MemberAdd,
    MemberResponse,
    RewardResponse,
    RoleChange,
    VisibilityRequest,
    VisibilityResponse,
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
    record_consent,
    remove_member,
    update_group,
)
from src.schemas import GroupContext

router = APIRouter()


# ---------------------------------------------------------------------------
# Agreement Templates (no group_id needed — placed before /{group_id} routes)
# ---------------------------------------------------------------------------


@router.get("/agreement-templates")
async def list_agreement_templates(
    auth: GroupContext = Depends(get_current_user),
):
    """List all available agreement templates."""
    from src.groups.agreement import get_templates

    return get_templates()


# ---------------------------------------------------------------------------
# Emergency Contacts & Agreement endpoints (under /{group_id})
# ---------------------------------------------------------------------------


@router.get("/{group_id}/agreement")
async def get_agreement(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the active agreement for a group."""
    from src.groups.agreement import get_active_agreement

    agreement = await get_active_agreement(db, group_id)
    if not agreement:
        return None
    return _agreement_to_dict(agreement)


@router.post("/{group_id}/agreement", status_code=201)
async def create_agreement_endpoint(
    group_id: UUID,
    body: AgreementCreateRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agreement from a template."""
    from src.groups.agreement import create_agreement

    agreement = await create_agreement(db, group_id, body.template_id, auth.user_id)
    return _agreement_to_dict(agreement)


@router.patch("/{group_id}/agreement")
async def update_agreement_endpoint(
    group_id: UUID,
    body: AgreementUpdateRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update rules of the active agreement."""
    from src.exceptions import NotFoundError
    from src.groups.agreement import get_active_agreement, update_agreement

    agreement = await get_active_agreement(db, group_id)
    if not agreement:
        raise NotFoundError("Agreement")
    updated = await update_agreement(db, agreement.id, body.rules)
    return _agreement_to_dict(updated)


@router.post("/{group_id}/agreement/sign", status_code=201)
async def sign_agreement_endpoint(
    group_id: UUID,
    body: AgreementSignRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Member signs the active agreement."""
    from src.exceptions import NotFoundError
    from src.groups.agreement import get_active_agreement, sign_agreement

    agreement = await get_active_agreement(db, group_id)
    if not agreement:
        raise NotFoundError("Agreement")
    updated = await sign_agreement(db, agreement.id, UUID(body.member_id), body.name)
    return _agreement_to_dict(updated)


@router.post("/{group_id}/agreement/review")
async def review_agreement_endpoint(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the active agreement as reviewed."""
    from src.exceptions import NotFoundError
    from src.groups.agreement import get_active_agreement, mark_reviewed

    agreement = await get_active_agreement(db, group_id)
    if not agreement:
        raise NotFoundError("Agreement")
    updated = await mark_reviewed(db, agreement.id)
    return _agreement_to_dict(updated)


def _agreement_to_dict(agreement) -> dict:
    """Convert a FamilyAgreement to a JSON-safe dict."""
    return {
        "id": str(agreement.id),
        "group_id": str(agreement.group_id),
        "title": agreement.title,
        "template_id": agreement.template_id,
        "rules": agreement.rules,
        "signed_by_parent": str(agreement.signed_by_parent) if agreement.signed_by_parent else None,
        "signed_by_parent_at": agreement.signed_by_parent_at.isoformat() if agreement.signed_by_parent_at else None,
        "signed_by_members": agreement.signed_by_members or [],
        "active": agreement.active,
        "review_due": agreement.review_due.isoformat() if agreement.review_due else None,
        "last_reviewed": agreement.last_reviewed.isoformat() if agreement.last_reviewed else None,
        "created_at": agreement.created_at.isoformat() if agreement.created_at else None,
    }


# ---------------------------------------------------------------------------
# Emergency Contacts CRUD
# ---------------------------------------------------------------------------


@router.get("/{group_id}/emergency-contacts")
async def list_emergency_contacts_endpoint(
    group_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List emergency contacts for a group."""
    from src.groups.emergency_contacts import list_emergency_contacts

    contacts = await list_emergency_contacts(db, group_id)
    return [_contact_to_dict(c) for c in contacts]


@router.post("/{group_id}/emergency-contacts", status_code=201)
async def add_emergency_contact_endpoint(
    group_id: UUID,
    body: EmergencyContactCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an emergency contact."""
    from src.groups.emergency_contacts import add_emergency_contact

    contact = await add_emergency_contact(db, group_id, body.model_dump())
    return _contact_to_dict(contact)


@router.patch("/{group_id}/emergency-contacts/{contact_id}")
async def update_emergency_contact_endpoint(
    group_id: UUID,
    contact_id: UUID,
    body: EmergencyContactUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an emergency contact."""
    from src.groups.emergency_contacts import update_emergency_contact

    contact = await update_emergency_contact(db, contact_id, body.model_dump(exclude_none=True))
    return _contact_to_dict(contact)


@router.delete("/{group_id}/emergency-contacts/{contact_id}", status_code=204)
async def remove_emergency_contact_endpoint(
    group_id: UUID,
    contact_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an emergency contact."""
    from src.groups.emergency_contacts import remove_emergency_contact

    await remove_emergency_contact(db, contact_id)
    return None


def _contact_to_dict(contact) -> dict:
    """Convert an EmergencyContact to a JSON-safe dict."""
    return {
        "id": str(contact.id),
        "group_id": str(contact.group_id),
        "name": contact.name,
        "relationship": contact.relationship,
        "phone": contact.phone,
        "email": contact.email,
        "notify_on": contact.notify_on or [],
        "consent_given": contact.consent_given,
        "consent_given_at": contact.consent_given_at.isoformat() if contact.consent_given_at else None,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


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


@router.post("/{group_id}/members/{member_id}/consent", response_model=ConsentResponse, status_code=201)
async def record_consent_endpoint(
    group_id: UUID,
    member_id: UUID,
    data: ConsentCreate,
    request: Request,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record guardian consent for an underage member."""
    ip_address = request.client.host if request.client else None
    consent = await record_consent(
        db, group_id, member_id, auth.user_id,
        consent_type=data.consent_type,
        ip_address=ip_address,
        evidence=data.evidence,
    )
    return consent


@router.post("/invitations/{token}/accept", response_model=MemberResponse, status_code=201)
async def accept_invitation_endpoint(
    token: str,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a group invitation (FR-004)."""
    member = await accept_invitation(db, token, auth.user_id)
    return member


# ─── Sibling Privacy Controls (F11) ─────────────────────────────────────────


@router.get("/{group_id}/members/{member_id}/visibility", response_model=VisibilityResponse)
async def get_visibility(
    group_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get visibility config for a member."""
    await get_group(db, group_id, auth.user_id)  # verify access
    visible_to = await get_member_visibility(db, group_id, member_id)
    return VisibilityResponse(
        group_id=group_id,
        member_id=member_id,
        visible_to=visible_to,
        is_restricted=len(visible_to) > 0,
    )


@router.put("/{group_id}/members/{member_id}/visibility", response_model=VisibilityResponse)
async def set_visibility(
    group_id: UUID,
    member_id: UUID,
    data: VisibilityRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set which parents can see this child's data."""
    from src.groups.service import _require_admin
    await _require_admin(db, group_id, auth.user_id)

    visible_to = await set_member_visibility(db, group_id, member_id, data.visible_to)
    return VisibilityResponse(
        group_id=group_id,
        member_id=member_id,
        visible_to=visible_to,
        is_restricted=len(visible_to) > 0,
    )


@router.get("/{group_id}/members/{member_id}/self-view", response_model=ChildSelfViewResponse)
async def get_self_view(
    group_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get self-view config for a member."""
    await get_group(db, group_id, auth.user_id)  # verify access
    self_view = await get_child_self_view(db, group_id, member_id)
    if self_view:
        return ChildSelfViewResponse(
            group_id=group_id,
            member_id=member_id,
            enabled=self_view.enabled,
            sections=self_view.sections,
        )
    return ChildSelfViewResponse(
        group_id=group_id,
        member_id=member_id,
        enabled=False,
        sections=[],
    )


@router.put("/{group_id}/members/{member_id}/self-view", response_model=ChildSelfViewResponse)
async def set_self_view(
    group_id: UUID,
    member_id: UUID,
    data: ChildSelfViewRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable/configure self-view for a member."""
    from src.groups.service import _require_admin
    await _require_admin(db, group_id, auth.user_id)

    if data.enabled:
        self_view = await enable_child_self_view(db, group_id, member_id, data.sections)
        return ChildSelfViewResponse(
            group_id=group_id,
            member_id=member_id,
            enabled=self_view.enabled,
            sections=self_view.sections,
        )
    else:
        await disable_child_self_view(db, group_id, member_id)
        return ChildSelfViewResponse(
            group_id=group_id,
            member_id=member_id,
            enabled=False,
            sections=[],
        )


# ─── AI Usage Allowance Rewards (F14) ───────────────────────────────────────


@router.get("/{group_id}/members/{member_id}/rewards", response_model=list[RewardResponse])
async def get_rewards(
    group_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List rewards for a member."""
    await get_group(db, group_id, auth.user_id)  # verify access
    rewards = await list_member_rewards(db, group_id, member_id)
    return [
        RewardResponse(
            id=r.id,
            group_id=r.group_id,
            member_id=r.member_id,
            reward_type=r.reward_type,
            trigger=r.trigger,
            trigger_description=r.trigger_description,
            value=r.value,
            earned_at=r.earned_at,
            expires_at=r.expires_at,
            redeemed=r.redeemed,
        )
        for r in rewards
    ]


@router.post("/{group_id}/members/{member_id}/rewards/check", response_model=list[RewardResponse])
async def check_rewards(
    group_id: UUID,
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger reward evaluation for a member."""
    await get_group(db, group_id, auth.user_id)  # verify access
    awarded = await check_and_award_rewards(db, group_id, member_id)
    return [
        RewardResponse(
            id=r.id,
            group_id=r.group_id,
            member_id=r.member_id,
            reward_type=r.reward_type,
            trigger=r.trigger,
            trigger_description=r.trigger_description,
            value=r.value,
            earned_at=r.earned_at,
            expires_at=r.expires_at,
            redeemed=r.redeemed,
        )
        for r in awarded
    ]
