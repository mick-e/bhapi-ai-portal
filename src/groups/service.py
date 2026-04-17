"""Groups service — business logic for group management."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance import ConsentRecord
from src.constants import MAX_FAMILY_MEMBERS, MAX_GROUP_MEMBERS, MAX_GROUPS_PER_USER
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.groups.consent import get_consent_type, requires_consent
from src.groups.models import Group, GroupMember, Invitation
from src.groups.schemas import GroupCreate, GroupResponse, InvitationCreate, MemberAdd

logger = structlog.get_logger()


async def create_group(db: AsyncSession, user_id: UUID, data: GroupCreate) -> Group:
    """Create a new group."""
    # Check group limit per user
    result = await db.execute(
        select(func.count(Group.id)).where(Group.owner_id == user_id)
    )
    count = result.scalar() or 0
    if count >= MAX_GROUPS_PER_USER:
        raise ValidationError(f"Maximum {MAX_GROUPS_PER_USER} groups per user")

    group = Group(
        id=uuid4(),
        name=data.name,
        type=data.type,
        owner_id=user_id,
        settings=data.settings or {},
    )
    db.add(group)

    # Add owner as admin member
    role = "parent" if data.type == "family" else f"{data.type}_admin"
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=user_id,
        role=role,
        display_name="Owner",
    )
    db.add(member)
    await db.flush()
    await db.refresh(group, ["members"])

    logger.info("group_created", group_id=str(group.id), type=data.type)
    return group


async def get_group(db: AsyncSession, group_id: UUID, user_id: UUID) -> Group:
    """Get a group by ID. Verifies user is a member."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    # Verify membership
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    if not member_result.scalar_one_or_none():
        raise ForbiddenError("You are not a member of this group")

    return group


async def list_user_groups(db: AsyncSession, user_id: UUID) -> list[Group]:
    """List all groups a user belongs to."""
    result = await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
    )
    return list(result.scalars().all())


async def update_group(
    db: AsyncSession, group_id: UUID, user_id: UUID,
    name: str | None = None, settings: dict | None = None,
) -> Group:
    """Update group settings. Requires admin role."""
    group = await get_group(db, group_id, user_id)
    await _require_admin(db, group_id, user_id)

    if name is not None:
        group.name = name
    if settings is not None:
        group.settings = settings

    await db.flush()
    await db.refresh(group)
    return group


async def delete_group(db: AsyncSession, group_id: UUID, user_id: UUID) -> None:
    """Soft-delete a group. Owner only."""
    group = await get_group(db, group_id, user_id)
    if group.owner_id != user_id:
        raise ForbiddenError("Only the group owner can delete the group")
    group.soft_delete()
    await db.flush()
    logger.info("group_deleted", group_id=str(group_id))


async def add_member(
    db: AsyncSession, group_id: UUID, user_id: UUID, data: MemberAdd, jurisdiction: str = "us"
) -> GroupMember:
    """Add a member to a group. Requires admin role.

    If the member is under the consent threshold for their jurisdiction,
    a ConsentRecord must be created before capture events can be processed.
    """
    await _require_admin(db, group_id, user_id)

    # Determine cap based on group type
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    cap = MAX_FAMILY_MEMBERS if group.type == "family" else MAX_GROUP_MEMBERS

    # Check member count
    result = await db.execute(
        select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
    )
    count = result.scalar() or 0
    if count >= cap:
        raise ValidationError(f"Maximum {cap} members per {group.type} group")

    member = GroupMember(
        id=uuid4(),
        group_id=group_id,
        user_id=data.user_id,
        role=data.role,
        display_name=data.display_name,
        date_of_birth=data.date_of_birth,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    # Check if consent is required for underage member
    if data.date_of_birth and requires_consent(data.date_of_birth, jurisdiction):
        consent_type = get_consent_type(data.date_of_birth, jurisdiction)
        logger.info(
            "consent_required",
            group_id=str(group_id),
            member_id=str(member.id),
            consent_type=consent_type,
            jurisdiction=jurisdiction,
        )

    logger.info("member_added", group_id=str(group_id), member_id=str(member.id))

    # Update per-seat billing for school/club
    if group.type in ("school", "club"):
        from src.billing.service import update_seat_count
        await update_seat_count(db, group_id)

    return member


async def remove_member(db: AsyncSession, group_id: UUID, member_id: UUID, user_id: UUID) -> None:
    """Remove a member from a group. Requires admin role."""
    await _require_admin(db, group_id, user_id)

    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    # Need group type before deleting member
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()

    await db.delete(member)
    await db.flush()
    logger.info("member_removed", group_id=str(group_id), member_id=str(member_id))

    # Update per-seat billing for school/club
    if group and group.type in ("school", "club"):
        from src.billing.service import update_seat_count
        await update_seat_count(db, group_id)


async def change_member_role(
    db: AsyncSession, group_id: UUID, member_id: UUID,
    user_id: UUID, new_role: str,
) -> GroupMember:
    """Change a member's role. Requires admin role."""
    await _require_admin(db, group_id, user_id)

    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id, GroupMember.group_id == group_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    member.role = new_role
    await db.flush()
    await db.refresh(member)
    return member


async def create_invitation(
    db: AsyncSession, group_id: UUID, user_id: UUID, data: InvitationCreate
) -> Invitation:
    """Create a group invitation. Requires admin role."""
    admin_member = await _require_admin(db, group_id, user_id)

    token = secrets.token_urlsafe(32)
    consent_needed = False  # Will be determined when invitation is accepted

    invitation = Invitation(
        id=uuid4(),
        group_id=group_id,
        invited_by=user_id,
        email=data.email,
        role=data.role,
        token=token,
        status="pending",
        consent_required=consent_needed,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()
    await db.refresh(invitation)

    # Send invitation email
    try:
        result = await db.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        group_name = group.name if group else "your group"

        from src.email.service import send_email
        from src.email.templates import group_invitation as invitation_template

        invitation_url = f"https://bhapi.ai/invite/{token}"
        subject, html, plain = invitation_template(
            inviter_name=admin_member.display_name,
            group_name=group_name,
            role=data.role,
            invitation_url=invitation_url,
        )
        await send_email(
            to_email=data.email,
            subject=subject,
            html_content=html,
            plain_content=plain,
            group_id=str(group_id),
        )
    except Exception as exc:
        logger.error("invitation_email_failed", email=data.email, error=str(exc))

    logger.info("invitation_created", group_id=str(group_id), email=data.email)
    return invitation


async def accept_invitation(db: AsyncSession, token: str, user_id: UUID) -> GroupMember:
    """Accept a group invitation."""
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise NotFoundError("Invitation")
    if invitation.status != "pending":
        raise ValidationError("Invitation is no longer valid")
    if invitation.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.flush()
        raise ValidationError("Invitation has expired")

    # Check member cap for the group
    group_result = await db.execute(select(Group).where(Group.id == invitation.group_id))
    group = group_result.scalar_one_or_none()
    if group:
        cap = MAX_FAMILY_MEMBERS if group.type == "family" else MAX_GROUP_MEMBERS
        count_result = await db.execute(
            select(func.count(GroupMember.id)).where(GroupMember.group_id == invitation.group_id)
        )
        count = count_result.scalar() or 0
        if count >= cap:
            raise ValidationError(f"Maximum {cap} members per {group.type} group")

    # Create member
    member = GroupMember(
        id=uuid4(),
        group_id=invitation.group_id,
        user_id=user_id,
        role=invitation.role,
        display_name=invitation.email.split("@")[0],
    )
    db.add(member)

    invitation.status = "accepted"
    await db.flush()
    await db.refresh(member)

    logger.info("invitation_accepted", group_id=str(invitation.group_id))
    return member


async def list_members(db: AsyncSession, group_id: UUID, user_id: UUID) -> list[GroupMember]:
    """List all members of a group."""
    await get_group(db, group_id, user_id)  # Verify access
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    return list(result.scalars().all())


async def _require_admin(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
    """Require that the user has admin role in the group."""
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise ForbiddenError("You are not a member of this group")

    admin_roles = {"parent", "school_admin", "club_admin"}
    if member.role not in admin_roles:
        raise ForbiddenError("Admin role required for this action")

    return member


async def record_consent(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    user_id: UUID,
    consent_type: str,
    ip_address: str | None = None,
    evidence: str | None = None,
) -> "ConsentRecord":
    """Record guardian consent for an underage member.

    Args:
        group_id: The group the member belongs to.
        member_id: The member requiring consent.
        user_id: The admin/parent recording consent.
        consent_type: Type of consent (coppa, gdpr, lgpd, ai_interaction, monitoring).
        ip_address: IP of the person giving consent.
        evidence: Reference to signed consent form, etc.
    """
    await _require_admin(db, group_id, user_id)

    from src.compliance.models import ConsentRecord

    record = ConsentRecord(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        consent_type=consent_type,
        parent_user_id=user_id,
        ip_address=ip_address,
        evidence=evidence,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(
        "consent_recorded",
        group_id=str(group_id),
        member_id=str(member_id),
        consent_type=consent_type,
    )
    return record


async def check_member_consent(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> bool:
    """Check if a member has all required consent records.

    Returns True if no consent is needed or consent has been given.
    Returns False if consent is required but not yet recorded.
    """
    # Get member to check date_of_birth
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member or not member.date_of_birth:
        return True  # No DOB = no consent required

    if not requires_consent(member.date_of_birth):
        return True  # Adult, no consent needed

    # Check for active consent records (given_at set, withdrawn_at null)
    from src.compliance.models import ConsentRecord

    consent_result = await db.execute(
        select(func.count(ConsentRecord.id)).where(
            ConsentRecord.group_id == group_id,
            ConsentRecord.member_id == member_id,
            ConsentRecord.withdrawn_at.is_(None),
        )
    )
    count = consent_result.scalar() or 0
    return count > 0


async def check_family_agreement_signed(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> bool:
    """Check if a member has signed the family agreement for their group.
    Returns True if agreement exists and member has signed it.
    Returns False if no agreement exists or member hasn't signed.
    Signatures are stored as JSON in FamilyAgreement.signed_by_members.
    """
    from src.groups.agreement import get_active_agreement

    agreement = await get_active_agreement(db, group_id)
    if not agreement:
        return False

    # Check if member has signed (signatures stored as JSON list)
    signed_members = agreement.signed_by_members or []
    return any(s.get("member_id") == str(member_id) for s in signed_members)


def group_to_response(group: Group) -> GroupResponse:
    """Convert Group model to GroupResponse schema."""
    return GroupResponse(
        id=group.id,
        name=group.name,
        type=group.type,
        owner_id=group.owner_id,
        settings=group.settings,
        created_at=group.created_at,
        member_count=len(group.members) if group.members else 0,
    )
