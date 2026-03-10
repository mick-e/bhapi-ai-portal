"""E2E tests for SSO auto-provisioner."""

import pytest
from uuid import uuid4

from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.integrations.sso_models import SSOConfig
from src.integrations.sso_provisioner import auto_provision_member
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_auto_provision_creates_member(test_session):
    """Happy path: auto-provisioning creates a new GroupMember for a school."""
    group, owner_id = await make_test_group(
        test_session, name="School A", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="school-a.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    # Create a user that will be provisioned
    user = User(
        id=uuid4(),
        email="student@school-a.com",
        display_name="Student One",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "student@school-a.com",
            "display_name": "Student One",
            "external_id": "ext-123",
        },
    )

    assert member is not None
    assert member.group_id == group.id
    assert member.display_name == "Student One"
    assert member.role == "member"
    assert member.user_id == user.id


@pytest.mark.asyncio
async def test_auto_provision_respects_family_cap(test_session):
    """Family cap enforcement: provisioning should fail when 5 members exist."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="family.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    # Add 5 members to reach the family cap of 5
    for i in range(5):
        m = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name=f"Member {i}",
        )
        test_session.add(m)
    await test_session.flush()

    # Create a user for the 6th member attempt
    user = User(
        id=uuid4(),
        email="extra@family.com",
        display_name="Extra Member",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    # Should return None because cap is reached
    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "extra@family.com",
            "display_name": "Extra Member",
            "external_id": "ext-cap",
        },
    )

    assert member is None


@pytest.mark.asyncio
async def test_auto_provision_returns_existing_member(test_session):
    """Duplicate detection: returns existing member instead of creating a new one."""
    group, owner_id = await make_test_group(
        test_session, name="School B", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="microsoft_entra",
        tenant_id="schoolb.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    # Create user and add them as existing member
    user = User(
        id=uuid4(),
        email="existing@schoolb.com",
        display_name="Existing User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    existing_member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=user.id,
        role="member",
        display_name="Existing User",
    )
    test_session.add(existing_member)
    await test_session.flush()

    # Should return the existing member, not create a new one
    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "existing@schoolb.com",
            "display_name": "Existing User",
            "external_id": "ext-existing",
        },
    )

    assert member is not None
    assert member.id == existing_member.id


@pytest.mark.asyncio
async def test_auto_provision_school_no_cap_at_five(test_session):
    """School groups should NOT enforce the family cap of 5."""
    group, owner_id = await make_test_group(
        test_session, name="Big School", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="bigschool.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    # Add 5 members (which would hit family cap)
    for i in range(5):
        m = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name=f"Student {i}",
        )
        test_session.add(m)
    await test_session.flush()

    # 6th member should still be allowed for a school
    user = User(
        id=uuid4(),
        email="student6@bigschool.com",
        display_name="Student Six",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "student6@bigschool.com",
            "display_name": "Student Six",
            "external_id": "ext-6",
        },
    )

    assert member is not None
    assert member.display_name == "Student Six"


@pytest.mark.asyncio
async def test_auto_provision_returns_none_if_disabled(test_session):
    """Auto-provisioning returns None when auto_provision_members is False."""
    group, owner_id = await make_test_group(
        test_session, name="School C", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="schoolc.com",
        auto_provision_members=False,
    )
    test_session.add(sso)
    await test_session.flush()

    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "student@schoolc.com",
            "display_name": "Student",
            "external_id": "ext-disabled",
        },
    )

    assert member is None


@pytest.mark.asyncio
async def test_auto_provision_no_sso_config(test_session):
    """Auto-provisioning returns None when no SSO config exists for the group."""
    group, owner_id = await make_test_group(
        test_session, name="No SSO", group_type="school"
    )

    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "nobody@nowhere.com",
            "display_name": "Nobody",
            "external_id": "ext-none",
        },
    )

    assert member is None


@pytest.mark.asyncio
async def test_auto_provision_user_not_in_db(test_session):
    """Creates member with user_id=None when the user has no account yet."""
    group, owner_id = await make_test_group(
        test_session, name="School D", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="schoold.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    # No user record exists for this email
    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "newstudent@schoold.com",
            "display_name": "New Student",
            "external_id": "ext-new",
        },
    )

    assert member is not None
    assert member.user_id is None
    assert member.display_name == "New Student"
    assert member.group_id == group.id


@pytest.mark.asyncio
async def test_auto_provision_fallback_display_name(test_session):
    """Uses email local part as display_name when none provided."""
    group, owner_id = await make_test_group(
        test_session, name="School E", group_type="school"
    )

    sso = SSOConfig(
        id=uuid4(),
        group_id=group.id,
        provider="google_workspace",
        tenant_id="schoole.com",
        auto_provision_members=True,
    )
    test_session.add(sso)
    await test_session.flush()

    member = await auto_provision_member(
        db=test_session,
        group_id=group.id,
        sso_user_info={
            "email": "janedoe@schoole.com",
            "display_name": "",
            "external_id": "ext-fallback",
        },
    )

    assert member is not None
    assert member.display_name == "janedoe"
