"""Unit tests for the contacts module — contact requests, parent approval, blocking."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.contacts.models import Contact
from src.contacts.service import (
    approve_as_parent,
    block_contact,
    get_pending_approvals,
    list_contacts,
    respond_to_request,
    send_request,
)
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.social.models import Profile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession, **kwargs) -> User:
    """Create a test user."""
    uid = kwargs.pop("id", None) or uuid.uuid4()
    user = User(
        id=uid,
        email=kwargs.pop("email", f"test-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.pop("display_name", "Test User"),
        account_type=kwargs.pop("account_type", "family"),
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_profile(
    session: AsyncSession, user_id: uuid.UUID, age_tier: str = "teen",
) -> Profile:
    """Create a social profile for a user."""
    today = datetime.now(timezone.utc).date()
    if age_tier == "young":
        dob = today.replace(year=today.year - 7)
    elif age_tier == "preteen":
        dob = today.replace(year=today.year - 11)
    else:
        dob = today.replace(year=today.year - 14)

    profile = Profile(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Test User",
        date_of_birth=dob,
        age_tier=age_tier,
        visibility="friends_only",
    )
    session.add(profile)
    await session.flush()
    return profile


async def _make_family_group(
    session: AsyncSession, parent_id: uuid.UUID, child_id: uuid.UUID,
) -> Group:
    """Create a family group with parent and child members."""
    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=parent_id,
    )
    session.add(group)
    await session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=parent_id,
        role="parent",
        display_name="Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=child_id,
        role="member",
        display_name="Child",
    )
    session.add_all([parent_member, child_member])
    await session.flush()
    return group


# ---------------------------------------------------------------------------
# Tests — Send Request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_request_basic(test_session):
    """Send a basic contact request between two teens."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    assert contact.status == "pending"
    assert contact.parent_approval_status == "not_required"
    assert contact.requester_id == user1.id
    assert contact.target_id == user2.id


@pytest.mark.asyncio
async def test_send_request_young_requires_parent_approval(test_session):
    """Young user's contact request requires parent approval."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "young")

    contact = await send_request(test_session, user1.id, user2.id)
    assert contact.parent_approval_status == "pending"


@pytest.mark.asyncio
async def test_send_request_preteen_requires_parent_approval(test_session):
    """Preteen user's contact request requires parent approval."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "preteen")

    contact = await send_request(test_session, user1.id, user2.id)
    assert contact.parent_approval_status == "pending"


@pytest.mark.asyncio
async def test_send_request_self_rejected(test_session):
    """Cannot send contact request to yourself."""
    user1 = await _make_user(test_session)
    with pytest.raises(ValidationError, match="yourself"):
        await send_request(test_session, user1.id, user1.id)


@pytest.mark.asyncio
async def test_send_request_duplicate_rejected(test_session):
    """Cannot send duplicate contact request."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    await send_request(test_session, user1.id, user2.id)
    with pytest.raises(ConflictError, match="already exists"):
        await send_request(test_session, user1.id, user2.id)


@pytest.mark.asyncio
async def test_send_request_reverse_duplicate_rejected(test_session):
    """Cannot send contact request if reverse request already exists."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")
    await _make_profile(test_session, user2.id, "teen")

    await send_request(test_session, user1.id, user2.id)
    with pytest.raises(ConflictError, match="already exists"):
        await send_request(test_session, user2.id, user1.id)


@pytest.mark.asyncio
async def test_send_request_blocked_user_rejected(test_session):
    """Cannot send contact request to a blocked user."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    await block_contact(test_session, user1.id, user2.id)
    with pytest.raises(ForbiddenError, match="Cannot send"):
        await send_request(test_session, user1.id, user2.id)


@pytest.mark.asyncio
async def test_send_request_max_contacts_limit(test_session):
    """Enforce max contacts limit based on age tier."""
    user1 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "young")  # max_contacts = 5

    # Create 5 accepted contacts
    for i in range(5):
        target = await _make_user(test_session)
        contact = Contact(
            id=uuid.uuid4(),
            requester_id=user1.id,
            target_id=target.id,
            status="accepted",
            parent_approval_status="not_required",
        )
        test_session.add(contact)
    await test_session.flush()

    # 6th should fail
    user_extra = await _make_user(test_session)
    with pytest.raises(ValidationError, match="Contact limit reached"):
        await send_request(test_session, user1.id, user_extra.id)


@pytest.mark.asyncio
async def test_send_request_explicit_age_tier(test_session):
    """Explicit age_tier parameter is used when provided."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    contact = await send_request(
        test_session, user1.id, user2.id, requester_age_tier="preteen",
    )
    assert contact.parent_approval_status == "pending"


# ---------------------------------------------------------------------------
# Tests — Respond to Request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_accept(test_session):
    """Target can accept a contact request."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    updated = await respond_to_request(test_session, contact.id, user2.id, "accept")
    assert updated.status == "accepted"


@pytest.mark.asyncio
async def test_respond_reject(test_session):
    """Target can reject a contact request."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    updated = await respond_to_request(test_session, contact.id, user2.id, "reject")
    assert updated.status == "rejected"


@pytest.mark.asyncio
async def test_respond_only_target_can_respond(test_session):
    """Only the target (not the requester) can respond."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    with pytest.raises(ForbiddenError, match="recipient"):
        await respond_to_request(test_session, contact.id, user1.id, "accept")


@pytest.mark.asyncio
async def test_respond_not_found(test_session):
    """Responding to nonexistent contact request raises NotFoundError."""
    user1 = await _make_user(test_session)
    with pytest.raises(NotFoundError):
        await respond_to_request(test_session, uuid.uuid4(), user1.id, "accept")


@pytest.mark.asyncio
async def test_respond_already_accepted(test_session):
    """Cannot respond to already-accepted request."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    await respond_to_request(test_session, contact.id, user2.id, "accept")

    with pytest.raises(ValidationError, match="already accepted"):
        await respond_to_request(test_session, contact.id, user2.id, "accept")


@pytest.mark.asyncio
async def test_respond_cannot_accept_pending_parent_approval(test_session):
    """Cannot accept when parent approval is pending."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "young")

    contact = await send_request(test_session, user1.id, user2.id)
    assert contact.parent_approval_status == "pending"

    with pytest.raises(ValidationError, match="parent approval"):
        await respond_to_request(test_session, contact.id, user2.id, "accept")


# ---------------------------------------------------------------------------
# Tests — Parent Approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_approve(test_session):
    """Parent can approve a child's contact request."""
    parent = await _make_user(test_session, display_name="Parent")
    child = await _make_user(test_session, display_name="Child")
    target = await _make_user(test_session, display_name="Target")
    await _make_profile(test_session, child.id, "young")
    await _make_family_group(test_session, parent.id, child.id)

    contact = await send_request(test_session, child.id, target.id)
    approval = await approve_as_parent(test_session, contact.id, parent.id, "approve")
    assert approval.decision == "approve"

    # Refresh the contact
    from sqlalchemy import select
    result = await test_session.execute(
        select(Contact).where(Contact.id == contact.id)
    )
    updated_contact = result.scalar_one()
    assert updated_contact.parent_approval_status == "approved"


@pytest.mark.asyncio
async def test_parent_deny(test_session):
    """Parent can deny a child's contact request."""
    parent = await _make_user(test_session)
    child = await _make_user(test_session)
    target = await _make_user(test_session)
    await _make_profile(test_session, child.id, "preteen")
    await _make_family_group(test_session, parent.id, child.id)

    contact = await send_request(test_session, child.id, target.id)
    approval = await approve_as_parent(test_session, contact.id, parent.id, "deny")
    assert approval.decision == "deny"

    from sqlalchemy import select
    result = await test_session.execute(
        select(Contact).where(Contact.id == contact.id)
    )
    updated_contact = result.scalar_one()
    assert updated_contact.parent_approval_status == "denied"
    assert updated_contact.status == "rejected"


@pytest.mark.asyncio
async def test_parent_approve_wrong_parent_rejected(test_session):
    """Non-parent user cannot approve."""
    parent = await _make_user(test_session)
    child = await _make_user(test_session)
    target = await _make_user(test_session)
    stranger = await _make_user(test_session)
    await _make_profile(test_session, child.id, "young")
    await _make_family_group(test_session, parent.id, child.id)

    contact = await send_request(test_session, child.id, target.id)
    with pytest.raises(ForbiddenError, match="parent"):
        await approve_as_parent(test_session, contact.id, stranger.id, "approve")


@pytest.mark.asyncio
async def test_parent_approve_not_required_rejected(test_session):
    """Cannot parent-approve a request that doesn't need it."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    parent = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    with pytest.raises(ValidationError, match="does not require"):
        await approve_as_parent(test_session, contact.id, parent.id, "approve")


@pytest.mark.asyncio
async def test_parent_approve_already_decided(test_session):
    """Cannot approve/deny twice."""
    parent = await _make_user(test_session)
    child = await _make_user(test_session)
    target = await _make_user(test_session)
    await _make_profile(test_session, child.id, "young")
    await _make_family_group(test_session, parent.id, child.id)

    contact = await send_request(test_session, child.id, target.id)
    await approve_as_parent(test_session, contact.id, parent.id, "approve")

    with pytest.raises(ValidationError, match="already"):
        await approve_as_parent(test_session, contact.id, parent.id, "approve")


# ---------------------------------------------------------------------------
# Tests — Block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_block_contact_new(test_session):
    """Block a user (no prior contact)."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    contact = await block_contact(test_session, user1.id, user2.id)
    assert contact.status == "blocked"


@pytest.mark.asyncio
async def test_block_contact_existing(test_session):
    """Block converts existing accepted contact to blocked."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    contact = await send_request(test_session, user1.id, user2.id)
    await respond_to_request(test_session, contact.id, user2.id, "accept")

    blocked = await block_contact(test_session, user1.id, user2.id)
    assert blocked.status == "blocked"


@pytest.mark.asyncio
async def test_block_self_rejected(test_session):
    """Cannot block yourself."""
    user1 = await _make_user(test_session)
    with pytest.raises(ValidationError, match="yourself"):
        await block_contact(test_session, user1.id, user1.id)


@pytest.mark.asyncio
async def test_block_already_blocked_rejected(test_session):
    """Cannot block an already-blocked user."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)

    await block_contact(test_session, user1.id, user2.id)
    with pytest.raises(ConflictError, match="already blocked"):
        await block_contact(test_session, user1.id, user2.id)


# ---------------------------------------------------------------------------
# Tests — List Contacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contacts_empty(test_session):
    """List contacts for user with no contacts."""
    user1 = await _make_user(test_session)
    result = await list_contacts(test_session, user1.id)
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_list_contacts_with_status_filter(test_session):
    """List contacts filtered by status."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    user3 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    c1 = await send_request(test_session, user1.id, user2.id)
    await respond_to_request(test_session, c1.id, user2.id, "accept")

    await send_request(test_session, user1.id, user3.id)  # still pending

    accepted = await list_contacts(test_session, user1.id, status="accepted")
    assert accepted["total"] == 1

    pending = await list_contacts(test_session, user1.id, status="pending")
    assert pending["total"] == 1

    all_contacts = await list_contacts(test_session, user1.id)
    assert all_contacts["total"] == 2


@pytest.mark.asyncio
async def test_list_contacts_pagination(test_session):
    """List contacts with pagination."""
    user1 = await _make_user(test_session)
    await _make_profile(test_session, user1.id, "teen")

    for _ in range(5):
        target = await _make_user(test_session)
        c = await send_request(test_session, user1.id, target.id)
        await respond_to_request(test_session, c.id, target.id, "accept")

    page1 = await list_contacts(test_session, user1.id, page=1, page_size=3)
    assert len(page1["items"]) == 3
    assert page1["total"] == 5
    assert page1["page"] == 1

    page2 = await list_contacts(test_session, user1.id, page=2, page_size=3)
    assert len(page2["items"]) == 2


# ---------------------------------------------------------------------------
# Tests — Pending Approvals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pending_approvals(test_session):
    """Parent sees pending approvals for their children."""
    parent = await _make_user(test_session)
    child = await _make_user(test_session)
    target = await _make_user(test_session)
    await _make_profile(test_session, child.id, "young")
    await _make_family_group(test_session, parent.id, child.id)

    await send_request(test_session, child.id, target.id)

    result = await get_pending_approvals(test_session, parent.id)
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_pending_approvals_empty(test_session):
    """Non-parent user sees no pending approvals."""
    user = await _make_user(test_session)
    result = await get_pending_approvals(test_session, user.id)
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_blocked_user_cannot_rerequest(test_session):
    """A blocked user cannot send a new request to the blocker."""
    user1 = await _make_user(test_session)
    user2 = await _make_user(test_session)
    await _make_profile(test_session, user2.id, "teen")

    await block_contact(test_session, user1.id, user2.id)

    with pytest.raises(ForbiddenError, match="Cannot send"):
        await send_request(test_session, user2.id, user1.id)
