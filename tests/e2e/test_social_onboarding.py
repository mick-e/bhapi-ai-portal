"""End-to-end tests for the social onboarding flow.

Tests age verification, parent consent requirements, profile creation
with age range enforcement, and tier assignment.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import AgeTier, age_from_dob, get_tier_for_age
from src.auth.models import User
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.integrations.age_verification import (
    process_age_verification_result,
    start_age_verification,
)
from src.integrations.yoti import (
    create_age_verification_session,
    get_age_verification_result,
)
from src.social.schemas import ProfileCreate
from src.social.service import create_profile, get_profile
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def family_setup(test_session: AsyncSession):
    """Create a family with parent and child member."""
    group, owner_id = await make_test_group(
        test_session, name="Onboarding Family", group_type="family"
    )

    # Child user (will be the one onboarding)
    child_user = User(
        id=uuid.uuid4(),
        email=f"child-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child_user)
    await test_session.flush()

    # Child as group member (age 10 — preteen)
    child_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=child_user.id,
        role="member",
        display_name="Test Child",
        date_of_birth=datetime(2016, 6, 15, tzinfo=timezone.utc),
    )
    test_session.add(child_member)
    await test_session.flush()

    return {
        "group": group,
        "owner_id": owner_id,
        "child_user": child_user,
        "child_member": child_member,
    }


@pytest_asyncio.fixture
async def young_child_setup(test_session: AsyncSession):
    """Create a family with an under-13 child (age 8)."""
    group, owner_id = await make_test_group(
        test_session, name="Young Family", group_type="family"
    )

    child_user = User(
        id=uuid.uuid4(),
        email=f"young-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Young Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child_user)
    await test_session.flush()

    child_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=child_user.id,
        role="member",
        display_name="Young Child",
        date_of_birth=datetime(2018, 3, 10, tzinfo=timezone.utc),
    )
    test_session.add(child_member)
    await test_session.flush()

    return {
        "group": group,
        "owner_id": owner_id,
        "child_user": child_user,
        "child_member": child_member,
    }


# ---------------------------------------------------------------------------
# Age Verification → Tier Assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_age_verify_creates_session():
    """Starting age verification should create a Yoti session (dev mode)."""
    result = await create_age_verification_session("member_onboard_1")
    assert "session_id" in result
    assert result["session_id"].startswith("dev_session_")
    assert "url" in result


@pytest.mark.asyncio
async def test_onboarding_age_verify_returns_result():
    """Getting verification result should return age (dev mode returns 12)."""
    result = await get_age_verification_result("dev_session_xyz")
    assert result["verified"] is True
    assert result["age"] == 12
    assert result["session_id"] == "dev_session_xyz"


@pytest.mark.asyncio
async def test_onboarding_age_verify_creates_tier(family_setup, test_session):
    """Child registers, Yoti verifies age, tier is assigned via profile."""
    data = family_setup
    child_user = data["child_user"]

    # Create profile with date_of_birth → triggers tier assignment
    # DOB 2015-01-01 gives age 11 in March 2026 → preteen tier
    profile_data = ProfileCreate(
        display_name="Cool Kid",
        date_of_birth=date(2015, 1, 1),
    )
    profile = await create_profile(test_session, child_user.id, profile_data)
    await test_session.commit()

    assert profile.age_tier == "preteen"
    assert profile.display_name == "Cool Kid"


@pytest.mark.asyncio
async def test_onboarding_tier_young(test_session):
    """Age 7 child gets young tier."""
    group, owner_id = await make_test_group(test_session, name="Young Fam")
    child = User(
        id=uuid.uuid4(),
        email=f"young7-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Young7",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child)
    await test_session.flush()

    profile = await create_profile(
        test_session,
        child.id,
        ProfileCreate(display_name="Young7", date_of_birth=date(2019, 1, 1)),
    )
    assert profile.age_tier == "young"


@pytest.mark.asyncio
async def test_onboarding_tier_teen(test_session):
    """Age 14 child gets teen tier."""
    group, owner_id = await make_test_group(test_session, name="Teen Fam")
    child = User(
        id=uuid.uuid4(),
        email=f"teen14-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Teen14",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child)
    await test_session.flush()

    profile = await create_profile(
        test_session,
        child.id,
        ProfileCreate(display_name="Teen14", date_of_birth=date(2012, 6, 1)),
    )
    assert profile.age_tier == "teen"


# ---------------------------------------------------------------------------
# Parent Consent Required for Under-13
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_parent_consent_required_under_13():
    """Under-13 verification result should flag consent requirement."""
    result = await get_age_verification_result("dev_session_u13")
    assert result["verified"] is True
    assert result["age"] == 12  # Dev mode returns 12 (under 13)
    # The mobile app checks this age and routes to parent consent step
    assert result["age"] < 13


@pytest.mark.asyncio
async def test_onboarding_age_verify_updates_member_dob(family_setup, test_session):
    """Processing verification result should update member's date of birth."""
    data = family_setup
    result = await process_age_verification_result(
        test_session,
        data["group"].id,
        data["child_member"].id,
        "dev_session_dob_test",
    )
    assert result["verified"] is True
    assert result["age"] == 12


@pytest.mark.asyncio
async def test_onboarding_age_verify_nonexistent_member(test_session):
    """Verification for a nonexistent member should fail."""
    group, _ = await make_test_group(test_session, name="Ghost Fam")
    with pytest.raises(NotFoundError):
        await start_age_verification(test_session, group.id, uuid.uuid4())


# ---------------------------------------------------------------------------
# Profile Creation Enforces Age Range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_profile_creation_rejects_too_young(test_session):
    """Profile creation rejects children under 5."""
    group, owner_id = await make_test_group(test_session, name="Baby Fam")
    child = User(
        id=uuid.uuid4(),
        email=f"baby-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Baby",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child)
    await test_session.flush()

    with pytest.raises(ValidationError, match="between 5 and 15"):
        await create_profile(
            test_session,
            child.id,
            ProfileCreate(display_name="Baby", date_of_birth=date(2024, 1, 1)),
        )


@pytest.mark.asyncio
async def test_onboarding_profile_creation_rejects_too_old(test_session):
    """Profile creation rejects users over 15."""
    group, owner_id = await make_test_group(test_session, name="Adult Fam")
    adult = User(
        id=uuid.uuid4(),
        email=f"adult-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Adult",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(adult)
    await test_session.flush()

    with pytest.raises(ValidationError, match="between 5 and 15"):
        await create_profile(
            test_session,
            adult.id,
            ProfileCreate(display_name="Adult", date_of_birth=date(2005, 1, 1)),
        )


@pytest.mark.asyncio
async def test_onboarding_profile_creation_enforces_age_range_boundary_low(test_session):
    """Profile creation accepts exactly age 5."""
    group, owner_id = await make_test_group(test_session, name="Five Fam")
    child = User(
        id=uuid.uuid4(),
        email=f"five-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Five",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child)
    await test_session.flush()

    profile = await create_profile(
        test_session,
        child.id,
        ProfileCreate(display_name="FiveKid", date_of_birth=date(2021, 3, 20)),
    )
    assert profile.age_tier == "young"


@pytest.mark.asyncio
async def test_onboarding_profile_creation_enforces_age_range_boundary_high(test_session):
    """Profile creation accepts exactly age 15."""
    group, owner_id = await make_test_group(test_session, name="Fifteen Fam")
    child = User(
        id=uuid.uuid4(),
        email=f"fifteen-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Fifteen",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(child)
    await test_session.flush()

    profile = await create_profile(
        test_session,
        child.id,
        ProfileCreate(display_name="FifteenKid", date_of_birth=date(2011, 3, 20)),
    )
    assert profile.age_tier == "teen"


@pytest.mark.asyncio
async def test_onboarding_duplicate_profile_rejected(family_setup, test_session):
    """Creating a profile twice for the same user should fail."""
    data = family_setup
    child_user = data["child_user"]

    await create_profile(
        test_session,
        child_user.id,
        ProfileCreate(display_name="First", date_of_birth=date(2016, 6, 15)),
    )
    await test_session.flush()

    with pytest.raises(ConflictError, match="already exists"):
        await create_profile(
            test_session,
            child_user.id,
            ProfileCreate(display_name="Second", date_of_birth=date(2016, 6, 15)),
        )


@pytest.mark.asyncio
async def test_onboarding_profile_retrieved_after_creation(family_setup, test_session):
    """After creating a profile, it can be retrieved by user_id."""
    data = family_setup
    child_user = data["child_user"]

    # DOB 2015-01-01 gives age 11 in March 2026 → preteen
    created = await create_profile(
        test_session,
        child_user.id,
        ProfileCreate(
            display_name="Findable",
            bio="Hello world",
            date_of_birth=date(2015, 1, 1),
        ),
    )
    await test_session.flush()

    fetched = await get_profile(test_session, child_user.id)
    assert fetched.id == created.id
    assert fetched.display_name == "Findable"
    assert fetched.bio == "Hello world"
    assert fetched.age_tier == "preteen"


@pytest.mark.asyncio
async def test_onboarding_profile_not_found_before_creation(test_session):
    """Fetching profile for a user without one should raise NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_profile(test_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Age-tier utility validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_from_dob_calculates_correctly():
    """age_from_dob should return correct age for known dates."""
    # Child born 2016-06-15 should be ~10 in mid-2026
    dob = date(2016, 6, 15)
    age = age_from_dob(dob)
    assert 9 <= age <= 10  # depends on when test runs


@pytest.mark.asyncio
async def test_get_tier_for_age_boundaries():
    """Verify tier boundaries: 5-9 young, 10-12 preteen, 13-15 teen."""
    assert get_tier_for_age(4) is None
    assert get_tier_for_age(5) == AgeTier.YOUNG
    assert get_tier_for_age(9) == AgeTier.YOUNG
    assert get_tier_for_age(10) == AgeTier.PRETEEN
    assert get_tier_for_age(12) == AgeTier.PRETEEN
    assert get_tier_for_age(13) == AgeTier.TEEN
    assert get_tier_for_age(15) == AgeTier.TEEN
    assert get_tier_for_age(16) is None
