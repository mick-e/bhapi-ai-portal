"""Unit tests for parental abuse safeguards — trusted adult, custody, teen privacy."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.moderation.parental_safeguards import (
    CustodyConfig,
    CustodyDisputeStatus,
    GuardianRole,
    HELPLINES,
    PRIVACY_TIER_DEFAULTS,
    PrivacyTier,
    TeenPrivacyConfig,
    TrustedAdultRequest,
    TrustedAdultStatus,
    add_primary_guardian,
    add_secondary_guardian,
    check_trusted_adult_visibility,
    get_guardian_access,
    get_parent_visible_data,
    get_trusted_adult_requests,
    request_trusted_adult,
    resolve_custody_dispute,
    set_custody_dispute,
    set_teen_privacy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def parent_user(test_session: AsyncSession):
    """Create a parent user."""
    user = User(
        id=uuid.uuid4(),
        email=f"parent-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def second_parent_user(test_session: AsyncSession):
    """Create a second parent user (for custody tests)."""
    user = User(
        id=uuid.uuid4(),
        email=f"parent2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Second Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def family_group(test_session: AsyncSession, parent_user):
    """Create a family group."""
    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=parent_user.id,
        settings={},
    )
    test_session.add(group)
    await test_session.flush()
    return group


@pytest_asyncio.fixture
async def parent_member(test_session: AsyncSession, family_group, parent_user):
    """Create a parent group member."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=parent_user.id,
        role="parent",
        display_name="Parent",
    )
    test_session.add(member)
    await test_session.flush()
    return member


@pytest_asyncio.fixture
async def second_parent_member(test_session: AsyncSession, family_group, second_parent_user):
    """Create a second parent group member."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=second_parent_user.id,
        role="parent",
        display_name="Second Parent",
    )
    test_session.add(member)
    await test_session.flush()
    return member


@pytest_asyncio.fixture
async def child_member(test_session: AsyncSession, family_group):
    """Create a child group member."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()
    return member


# ---------------------------------------------------------------------------
# Trusted Adult — NOT visible to parent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_trusted_adult_creates_record(test_session, child_member):
    """Requesting a trusted adult creates a database record."""
    result = await request_trusted_adult(
        test_session,
        child_member_id=child_member.id,
        trusted_adult_name="Aunt Jane",
        trusted_adult_contact="jane@example.com",
        reason="I don't feel safe",
    )
    assert result["request_id"] is not None
    assert result["status"] == TrustedAdultStatus.PENDING.value
    assert "helplines" in result
    assert len(result["helplines"]) > 0


@pytest.mark.asyncio
async def test_trusted_adult_request_not_visible_to_parent(
    test_session, child_member, parent_member,
):
    """Trusted adult request visibility check returns False for parents."""
    # Create a custody config so the parent is recognized as guardian
    await add_primary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    # Create a request
    await request_trusted_adult(
        test_session,
        child_member_id=child_member.id,
        reason="Need help",
    )

    # Check visibility: parent should NOT see
    visible = await check_trusted_adult_visibility(
        test_session,
        child_member_id=child_member.id,
        requester_member_id=parent_member.id,
    )
    assert visible is False


@pytest.mark.asyncio
async def test_trusted_adult_request_visible_to_non_guardian(
    test_session, child_member,
):
    """Trusted adult request visible to non-guardian (platform staff)."""
    staff_member_id = uuid.uuid4()  # Not a guardian

    visible = await check_trusted_adult_visibility(
        test_session,
        child_member_id=child_member.id,
        requester_member_id=staff_member_id,
    )
    assert visible is True


@pytest.mark.asyncio
async def test_trusted_adult_includes_helplines(test_session, child_member):
    """Trusted adult response includes helpline numbers."""
    result = await request_trusted_adult(
        test_session,
        child_member_id=child_member.id,
        jurisdiction="US",
    )
    helplines = result["helplines"]
    assert any("Childhelp" in h["name"] for h in helplines)


@pytest.mark.asyncio
async def test_trusted_adult_uk_helplines(test_session, child_member):
    """UK jurisdiction returns UK-specific helplines."""
    result = await request_trusted_adult(
        test_session,
        child_member_id=child_member.id,
        jurisdiction="UK",
    )
    helplines = result["helplines"]
    assert any("Childline" in h["name"] for h in helplines)


@pytest.mark.asyncio
async def test_trusted_adult_private_message(test_session, child_member):
    """Response includes reassuring private message."""
    result = await request_trusted_adult(
        test_session,
        child_member_id=child_member.id,
    )
    assert "private" in result["message"].lower()
    assert "not be shared" in result["message"].lower()


@pytest.mark.asyncio
async def test_get_trusted_adult_requests(test_session, child_member):
    """Can retrieve all requests for a child."""
    await request_trusted_adult(test_session, child_member_id=child_member.id, reason="First")
    await request_trusted_adult(test_session, child_member_id=child_member.id, reason="Second")

    requests = await get_trusted_adult_requests(test_session, child_member_id=child_member.id)
    assert len(requests) == 2


# ---------------------------------------------------------------------------
# Custody-aware access — primary/secondary roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_primary_guardian(test_session, child_member, parent_member):
    """Adding a primary guardian gives full permissions."""
    config = await add_primary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert config.role == GuardianRole.PRIMARY.value
    assert config.can_view_activity is True
    assert config.can_manage_settings is True
    assert config.can_approve_contacts is True


@pytest.mark.asyncio
async def test_add_secondary_guardian_limited(
    test_session, child_member, second_parent_member,
):
    """Secondary guardian has limited permissions by default."""
    config = await add_secondary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    assert config.role == GuardianRole.SECONDARY.value
    assert config.can_view_activity is True
    assert config.can_manage_settings is False
    assert config.can_approve_contacts is False


@pytest.mark.asyncio
async def test_duplicate_guardian_raises(
    test_session, child_member, parent_member,
):
    """Adding duplicate guardian raises ValidationError."""
    await add_primary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    with pytest.raises(ValidationError):
        await add_primary_guardian(
            test_session,
            child_member_id=child_member.id,
            guardian_member_id=parent_member.id,
        )


@pytest.mark.asyncio
async def test_get_guardian_access(test_session, child_member, parent_member):
    """Can retrieve guardian access configuration."""
    await add_primary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    config = await get_guardian_access(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert config is not None
    assert config.role == GuardianRole.PRIMARY.value


@pytest.mark.asyncio
async def test_get_guardian_access_nonexistent(test_session, child_member):
    """Returns None when no guardian config exists."""
    config = await get_guardian_access(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=uuid.uuid4(),
    )
    assert config is None


# ---------------------------------------------------------------------------
# Custody disputes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_custody_dispute_flags(
    test_session, child_member, second_parent_member,
):
    """Setting custody dispute restricts secondary guardian."""
    await add_secondary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    config = await set_custody_dispute(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
        notes="Custody under review",
    )
    assert config.dispute_status == CustodyDisputeStatus.FLAGGED.value
    assert config.can_manage_settings is False
    assert config.can_approve_contacts is False


@pytest.mark.asyncio
async def test_custody_dispute_nonexistent_raises(test_session, child_member):
    """Setting dispute on nonexistent config raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await set_custody_dispute(
            test_session,
            child_member_id=child_member.id,
            guardian_member_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_resolve_custody_dispute(
    test_session, child_member, second_parent_member,
):
    """Resolving a custody dispute updates status."""
    await add_secondary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    await set_custody_dispute(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    config = await resolve_custody_dispute(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    assert config.dispute_status == CustodyDisputeStatus.RESOLVED.value


# ---------------------------------------------------------------------------
# Teen privacy tiers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_tier_everything_visible(test_session, child_member):
    """Young tier (5-9): everything visible to parent."""
    config = await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.YOUNG,
    )
    assert config.posts_visible is True
    assert config.contacts_visible is True
    assert config.messages_visible is True
    assert config.activity_summary_only is False


@pytest.mark.asyncio
async def test_preteen_tier_posts_contacts_not_messages(test_session, child_member):
    """Preteen tier (10-12): posts+contacts visible, NOT messages."""
    config = await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.PRETEEN,
    )
    assert config.posts_visible is True
    assert config.contacts_visible is True
    assert config.messages_visible is False


@pytest.mark.asyncio
async def test_teen_tier_summary_and_flagged_only(test_session, child_member):
    """Teen tier (13-15): only summary + flagged content visible."""
    config = await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.TEEN,
    )
    assert config.posts_visible is False
    assert config.contacts_visible is False
    assert config.messages_visible is False
    assert config.activity_summary_only is True
    assert config.flagged_content_visible is True


@pytest.mark.asyncio
async def test_set_teen_privacy_updates_existing(test_session, child_member):
    """Updating privacy tier modifies existing config."""
    await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.YOUNG,
    )
    config = await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.TEEN,
    )
    assert config.privacy_tier == PrivacyTier.TEEN.value
    assert config.activity_summary_only is True


# ---------------------------------------------------------------------------
# Parent visible data (combined custody + privacy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_visible_data_default(test_session, child_member, parent_member):
    """Without configs, default visibility is full except trusted adult."""
    visibility = await get_parent_visible_data(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is True
    assert visibility["messages"] is True
    assert visibility["trusted_adult_requests"] is False


@pytest.mark.asyncio
async def test_parent_visible_data_teen_tier(
    test_session, child_member, parent_member,
):
    """Teen privacy tier restricts parent's data visibility."""
    await add_primary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    await set_teen_privacy(
        test_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.TEEN,
    )
    visibility = await get_parent_visible_data(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is False
    assert visibility["messages"] is False
    assert visibility["activity_summary"] is True
    assert visibility["flagged_content"] is True
    assert visibility["trusted_adult_requests"] is False


@pytest.mark.asyncio
async def test_parent_visible_data_custody_dispute(
    test_session, child_member, second_parent_member,
):
    """During custody dispute, secondary guardian view is restricted."""
    await add_secondary_guardian(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    await set_custody_dispute(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    visibility = await get_parent_visible_data(
        test_session,
        child_member_id=child_member.id,
        guardian_member_id=second_parent_member.id,
    )
    assert visibility["messages"] is False
    assert visibility["activity_detail"] is False
    assert visibility["contacts"] is False
    assert visibility["trusted_adult_requests"] is False


@pytest.mark.asyncio
async def test_trusted_adult_never_in_parent_visible_data(
    test_session, child_member, parent_member,
):
    """Trusted adult requests are NEVER in parent visible data, regardless of tier."""
    for tier in PrivacyTier:
        await set_teen_privacy(
            test_session,
            child_member_id=child_member.id,
            privacy_tier=tier,
        )
        visibility = await get_parent_visible_data(
            test_session,
            child_member_id=child_member.id,
            guardian_member_id=parent_member.id,
        )
        assert visibility["trusted_adult_requests"] is False, f"Failed for tier {tier}"
