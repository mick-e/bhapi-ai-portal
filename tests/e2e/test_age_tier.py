"""End-to-end tests for the age tier module."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.models import AgeTierConfig
from src.age_tier.rules import AgeTier, age_from_dob, get_tier_for_age
from src.age_tier.schemas import AgeTierConfigCreate
from src.age_tier.service import assign_tier, get_member_permissions, get_member_tier
from src.auth.models import User
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def group_with_members(test_session: AsyncSession):
    """Create a group with members of various ages."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    # Young child (age 7)
    young_child = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Young Child",
        date_of_birth=datetime(2019, 3, 15, tzinfo=timezone.utc),
    )
    # Preteen (age 11)
    preteen = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Preteen",
        date_of_birth=datetime(2015, 6, 20, tzinfo=timezone.utc),
    )
    # Teen (age 14)
    teen = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Teen",
        date_of_birth=datetime(2012, 1, 10, tzinfo=timezone.utc),
    )
    test_session.add_all([young_child, preteen, teen])
    await test_session.flush()

    return {
        "group": group,
        "owner": user,
        "young_child": young_child,
        "preteen": preteen,
        "teen": teen,
    }


# ---------------------------------------------------------------------------
# Service-level E2E tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_tier_young(test_session: AsyncSession, group_with_members):
    """Assign tier to young child (age 7)."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    config = await assign_tier(test_session, data)
    assert config.tier == "young"
    assert config.member_id == member.id


@pytest.mark.asyncio
async def test_assign_tier_preteen(test_session: AsyncSession, group_with_members):
    """Assign tier to preteen (age 11)."""
    member = group_with_members["preteen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    config = await assign_tier(test_session, data)
    assert config.tier == "preteen"


@pytest.mark.asyncio
async def test_assign_tier_teen(test_session: AsyncSession, group_with_members):
    """Assign tier to teen (age 14)."""
    member = group_with_members["teen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    config = await assign_tier(test_session, data)
    assert config.tier == "teen"


@pytest.mark.asyncio
async def test_assign_tier_upsert(test_session: AsyncSession, group_with_members):
    """Reassigning tier updates existing config (upsert)."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    config1 = await assign_tier(test_session, data)
    original_id = config1.id

    # Reassign with different jurisdiction
    data2 = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        jurisdiction="GB",
    )
    config2 = await assign_tier(test_session, data2)
    assert config2.id == original_id  # Same row
    assert config2.jurisdiction == "GB"


@pytest.mark.asyncio
async def test_assign_tier_with_overrides(test_session: AsyncSession, group_with_members):
    """Assign tier with feature overrides."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        feature_overrides={"can_message": True},
    )
    config = await assign_tier(test_session, data)
    assert config.feature_overrides == {"can_message": True}


@pytest.mark.asyncio
async def test_assign_tier_with_locked_features(test_session: AsyncSession, group_with_members):
    """Assign tier with locked features."""
    member = group_with_members["teen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        locked_features=["can_upload_video"],
    )
    config = await assign_tier(test_session, data)
    assert config.locked_features == ["can_upload_video"]


@pytest.mark.asyncio
async def test_assign_tier_invalid_age(test_session: AsyncSession, group_with_members):
    """Reject tier assignment for age outside range."""
    member = group_with_members["young_child"]
    # Age 2 — too young
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(ValidationError, match="outside the supported range"):
        await assign_tier(test_session, data)


@pytest.mark.asyncio
async def test_get_member_tier_found(test_session: AsyncSession, group_with_members):
    """Get existing tier config."""
    member = group_with_members["preteen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    await assign_tier(test_session, data)
    config = await get_member_tier(test_session, member.id)
    assert config.tier == "preteen"


@pytest.mark.asyncio
async def test_get_member_tier_not_found(test_session: AsyncSession):
    """Get tier for nonexistent member raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_member_tier(test_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_get_member_permissions_young(test_session: AsyncSession, group_with_members):
    """Get permissions for a young child."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    await assign_tier(test_session, data)
    perms = await get_member_permissions(test_session, member.id)
    assert perms["can_message"] is False
    assert perms["can_post"] is True
    assert perms["moderation_mode"] == "pre_publish"


@pytest.mark.asyncio
async def test_get_member_permissions_with_overrides(test_session: AsyncSession, group_with_members):
    """Permissions respect feature overrides."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        feature_overrides={"can_message": True},
    )
    await assign_tier(test_session, data)
    perms = await get_member_permissions(test_session, member.id)
    assert perms["can_message"] is True


@pytest.mark.asyncio
async def test_get_member_permissions_with_locked(test_session: AsyncSession, group_with_members):
    """Locked features override everything."""
    member = group_with_members["teen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        feature_overrides={"can_upload_video": True},
        locked_features=["can_upload_video"],
    )
    await assign_tier(test_session, data)
    perms = await get_member_permissions(test_session, member.id)
    assert perms["can_upload_video"] is False


@pytest.mark.asyncio
async def test_get_member_permissions_not_found(test_session: AsyncSession):
    """Permissions for nonexistent member raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_member_permissions(test_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_assign_tier_jurisdiction(test_session: AsyncSession, group_with_members):
    """Jurisdiction stored correctly."""
    member = group_with_members["preteen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
        jurisdiction="AU",
    )
    config = await assign_tier(test_session, data)
    assert config.jurisdiction == "AU"


@pytest.mark.asyncio
async def test_assign_tier_too_old(test_session: AsyncSession, group_with_members):
    """Reject tier assignment for age > 15."""
    member = group_with_members["young_child"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=datetime(2008, 1, 1, tzinfo=timezone.utc),  # Age 18
    )
    with pytest.raises(ValidationError, match="outside the supported range"):
        await assign_tier(test_session, data)


@pytest.mark.asyncio
async def test_permissions_teen_has_video(test_session: AsyncSession, group_with_members):
    """Teen tier has video upload enabled by default."""
    member = group_with_members["teen"]
    data = AgeTierConfigCreate(
        member_id=member.id,
        date_of_birth=member.date_of_birth,
    )
    await assign_tier(test_session, data)
    perms = await get_member_permissions(test_session, member.id)
    assert perms["can_upload_video"] is True
    assert perms["can_use_ai_chat"] is True
    assert perms["content_filter_level"] == "standard"
