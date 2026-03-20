"""Contacts module business logic — contact requests, parent approval, blocking."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import get_permissions, get_tier_for_age
from src.age_tier.rules import AgeTier
from src.contacts.models import Contact, ContactApproval
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError

logger = structlog.get_logger()


async def _get_user_age_tier(db: AsyncSession, user_id: UUID) -> str | None:
    """Get the age tier for a user from their social profile, or None."""
    from src.social.models import Profile

    result = await db.execute(
        select(Profile.age_tier).where(Profile.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    return row


async def _count_active_contacts(db: AsyncSession, user_id: UUID) -> int:
    """Count active (accepted) contacts for a user."""
    result = await db.execute(
        select(func.count()).select_from(Contact).where(
            or_(
                Contact.requester_id == user_id,
                Contact.target_id == user_id,
            ),
            Contact.status == "accepted",
        )
    )
    return result.scalar() or 0


async def _is_blocked(
    db: AsyncSession, user_id: UUID, target_id: UUID,
) -> bool:
    """Check if either user has blocked the other."""
    result = await db.execute(
        select(Contact.id).where(
            or_(
                (Contact.requester_id == user_id) & (Contact.target_id == target_id),
                (Contact.requester_id == target_id) & (Contact.target_id == user_id),
            ),
            Contact.status == "blocked",
        )
    )
    return result.scalar_one_or_none() is not None


async def _get_parent_for_user(db: AsyncSession, user_id: UUID) -> UUID | None:
    """Find the parent user for a child within their family group.

    Looks up the child's group membership, then finds the parent in that group.
    """
    from src.groups.models import GroupMember

    # Find the child's group
    child_member = await db.execute(
        select(GroupMember.group_id).where(GroupMember.user_id == user_id)
    )
    group_id = child_member.scalar_one_or_none()
    if not group_id:
        return None

    # Find the parent in that group
    parent_member = await db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id == group_id,
            GroupMember.role == "parent",
            GroupMember.user_id != user_id,
        )
    )
    return parent_member.scalar_one_or_none()


async def send_request(
    db: AsyncSession,
    requester_id: UUID,
    target_id: UUID,
    requester_age_tier: str | None = None,
) -> Contact:
    """Create a contact request.

    If requester is young/preteen (under 13), set parent_approval_status="pending".
    If teen or no tier, set to "not_required".
    Checks age_tier max_contacts limit. Prevents duplicate requests and blocked users.
    """
    if requester_id == target_id:
        raise ValidationError("Cannot send contact request to yourself")

    # Check if blocked
    if await _is_blocked(db, requester_id, target_id):
        raise ForbiddenError("Cannot send contact request to this user")

    # Check for existing request in either direction
    existing = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_id == requester_id) & (Contact.target_id == target_id),
                (Contact.requester_id == target_id) & (Contact.target_id == requester_id),
            ),
            Contact.status.in_(["pending", "accepted"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Contact request already exists between these users")

    # Determine age tier from profile if not provided
    if requester_age_tier is None:
        requester_age_tier = await _get_user_age_tier(db, requester_id)

    # Enforce max_contacts limit
    if requester_age_tier:
        tier = AgeTier(requester_age_tier)
        perms = get_permissions(tier)
        max_contacts = perms.get("max_contacts", 50)
        current_count = await _count_active_contacts(db, requester_id)
        if current_count >= max_contacts:
            raise ValidationError(
                f"Contact limit reached ({max_contacts}). "
                "Cannot send more contact requests."
            )

    # Determine parent approval requirement
    parent_approval_status = "not_required"
    if requester_age_tier in (AgeTier.YOUNG, AgeTier.PRETEEN):
        parent_approval_status = "pending"

    contact = Contact(
        id=uuid4(),
        requester_id=requester_id,
        target_id=target_id,
        status="pending",
        parent_approval_status=parent_approval_status,
    )
    db.add(contact)
    await db.flush()

    logger.info(
        "contact_request_sent",
        contact_id=str(contact.id),
        requester_id=str(requester_id),
        target_id=str(target_id),
        parent_approval=parent_approval_status,
    )

    return contact


async def respond_to_request(
    db: AsyncSession,
    contact_id: UUID,
    user_id: UUID,
    action: str,
) -> Contact:
    """Accept or reject a contact request. Only the target can respond.

    If parent approval is pending and action is "accept", the contact stays
    pending until the parent approves.
    """
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise NotFoundError("Contact request", str(contact_id))

    if contact.target_id != user_id:
        raise ForbiddenError("Only the recipient can respond to this request")

    if contact.status != "pending":
        raise ValidationError(f"Contact request is already {contact.status}")

    if action == "reject":
        contact.status = "rejected"
    elif action == "accept":
        if contact.parent_approval_status == "pending":
            # Target accepts, but parent hasn't approved yet — stay pending
            # We track acceptance by storing it but keep status pending
            raise ValidationError(
                "Cannot accept yet — parent approval is required"
            )
        elif contact.parent_approval_status == "denied":
            raise ValidationError("Parent has denied this contact request")
        else:
            contact.status = "accepted"

    await db.flush()

    logger.info(
        "contact_request_responded",
        contact_id=str(contact_id),
        user_id=str(user_id),
        action=action,
        new_status=contact.status,
    )

    return contact


async def approve_as_parent(
    db: AsyncSession,
    contact_id: UUID,
    parent_user_id: UUID,
    decision: str,
) -> ContactApproval:
    """Parent approves or denies a contact request.

    Only the parent of the requesting child can approve.
    On approval, the contact's parent_approval_status becomes "approved".
    The contact still needs the target to accept.
    """
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise NotFoundError("Contact request", str(contact_id))

    if contact.parent_approval_status == "not_required":
        raise ValidationError("This contact request does not require parent approval")

    if contact.parent_approval_status in ("approved", "denied"):
        raise ValidationError(
            f"Parent has already {contact.parent_approval_status} this request"
        )

    # Verify the parent is actually the parent of the requester
    parent_of_requester = await _get_parent_for_user(db, contact.requester_id)
    if parent_of_requester != parent_user_id:
        raise ForbiddenError("Only the parent of the requester can approve")

    now = datetime.now(timezone.utc)

    approval = ContactApproval(
        id=uuid4(),
        contact_id=contact_id,
        parent_user_id=parent_user_id,
        decision=decision,
        decided_at=now,
    )
    db.add(approval)

    if decision == "approve":
        contact.parent_approval_status = "approved"
    else:
        contact.parent_approval_status = "denied"
        contact.status = "rejected"

    await db.flush()

    logger.info(
        "contact_parent_approval",
        contact_id=str(contact_id),
        parent_user_id=str(parent_user_id),
        decision=decision,
    )

    return approval


async def block_contact(
    db: AsyncSession,
    user_id: UUID,
    target_user_id: UUID,
) -> Contact:
    """Block a user. Removes/replaces existing contact if any."""
    if user_id == target_user_id:
        raise ValidationError("Cannot block yourself")

    # Find existing contact in either direction
    result = await db.execute(
        select(Contact).where(
            or_(
                (Contact.requester_id == user_id) & (Contact.target_id == target_user_id),
                (Contact.requester_id == target_user_id) & (Contact.target_id == user_id),
            ),
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status == "blocked":
            raise ConflictError("User is already blocked")
        existing.status = "blocked"
        await db.flush()
        logger.info(
            "contact_blocked",
            contact_id=str(existing.id),
            blocker_id=str(user_id),
            blocked_id=str(target_user_id),
        )
        return existing

    # Create new blocked contact
    contact = Contact(
        id=uuid4(),
        requester_id=user_id,
        target_id=target_user_id,
        status="blocked",
        parent_approval_status="not_required",
    )
    db.add(contact)
    await db.flush()

    logger.info(
        "contact_blocked",
        contact_id=str(contact.id),
        blocker_id=str(user_id),
        blocked_id=str(target_user_id),
    )

    return contact


async def list_contacts(
    db: AsyncSession,
    user_id: UUID,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List user's contacts (both sent and received).

    Returns dict with items, total, page, page_size.
    """
    base_filter = or_(
        Contact.requester_id == user_id,
        Contact.target_id == user_id,
    )

    filters = [base_filter]
    if status:
        filters.append(Contact.status == status)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(Contact).where(*filters)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Contact)
        .where(*filters)
        .order_by(Contact.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_pending_approvals(
    db: AsyncSession,
    parent_user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List contacts awaiting parent approval for the parent's children.

    Finds all children of this parent (via GroupMember), then returns
    pending contact requests for those children.
    """
    from src.groups.models import GroupMember

    # Find groups where this user is a parent
    parent_groups_result = await db.execute(
        select(GroupMember.group_id).where(
            GroupMember.user_id == parent_user_id,
            GroupMember.role == "parent",
        )
    )
    parent_group_ids = [row[0] for row in parent_groups_result.all()]

    if not parent_group_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    # Find child user_ids in those groups (non-parent members)
    children_result = await db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id.in_(parent_group_ids),
            GroupMember.role != "parent",
            GroupMember.user_id.is_not(None),
        )
    )
    child_user_ids = [row[0] for row in children_result.all()]

    if not child_user_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    # Find pending approval contacts for these children
    filters = [
        Contact.requester_id.in_(child_user_ids),
        Contact.parent_approval_status == "pending",
    ]

    count_result = await db.execute(
        select(func.count()).select_from(Contact).where(*filters)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Contact)
        .where(*filters)
        .order_by(Contact.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
