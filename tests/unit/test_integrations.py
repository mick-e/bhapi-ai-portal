"""Unit tests for the integrations module.

Covers:
- _verify_group_access() helper — valid member, non-member 403, missing group
- SIS connection model creation and status transitions
- SSO config validation (provider types, required fields)
- Directory sync logic (user provisioning, deprovisioning)
- SIS roster sync logic
- Yoti age verification response parsing
- Auto-provisioning logic
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ForbiddenError, NotFoundError
from src.groups.models import Group, GroupMember
from src.integrations.models import SISConnection
from src.integrations.sso_models import SSOConfig
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def school_group(test_session: AsyncSession):
    """Create a school group with owner and a member."""
    owner = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
        display_name="School Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(owner)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test School",
        type="school",
        owner_id=owner.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=owner.id,
        role="admin",
        display_name="School Admin",
    )
    test_session.add(member)
    await test_session.flush()

    return {"group": group, "owner": owner, "member": member}


@pytest_asyncio.fixture
async def other_user(test_session: AsyncSession):
    """Create a user not in any group."""
    user = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


# ---------------------------------------------------------------------------
# _verify_group_access() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_group_access_same_group(test_session, school_group):
    """User whose auth.group_id matches passes immediately."""
    from src.integrations.router import _verify_group_access

    auth = GroupContext(
        user_id=school_group["owner"].id,
        group_id=school_group["group"].id,
        role="admin",
    )
    # Should not raise
    await _verify_group_access(auth, school_group["group"].id, test_session)


@pytest.mark.asyncio
async def test_verify_group_access_member_lookup(test_session, school_group):
    """User with different auth.group_id but is a member passes via DB lookup."""
    from src.integrations.router import _verify_group_access

    auth = GroupContext(
        user_id=school_group["owner"].id,
        group_id=uuid.uuid4(),  # different group
        role="admin",
    )
    # Owner is a member of the school group, so DB lookup should pass
    await _verify_group_access(auth, school_group["group"].id, test_session)


@pytest.mark.asyncio
async def test_verify_group_access_non_member_forbidden(test_session, school_group, other_user):
    """Non-member gets ForbiddenError."""
    from src.integrations.router import _verify_group_access

    auth = GroupContext(
        user_id=other_user.id,
        group_id=uuid.uuid4(),
        role="member",
    )
    with pytest.raises(ForbiddenError):
        await _verify_group_access(auth, school_group["group"].id, test_session)


@pytest.mark.asyncio
async def test_verify_group_access_nonexistent_group(test_session, other_user):
    """Access to a non-existent group raises ForbiddenError."""
    from src.integrations.router import _verify_group_access

    auth = GroupContext(
        user_id=other_user.id,
        group_id=uuid.uuid4(),
        role="member",
    )
    fake_group_id = uuid.uuid4()
    with pytest.raises(ForbiddenError):
        await _verify_group_access(auth, fake_group_id, test_session)


# ---------------------------------------------------------------------------
# SIS Connection model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sis_connection_creation(test_session, school_group):
    """SIS connection can be created with encrypted credentials."""
    conn = SISConnection(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="clever",
        credentials_encrypted=encrypt_credential("test-token-abc"),
        status="active",
        config_json={"district_id": "123"},
    )
    test_session.add(conn)
    await test_session.flush()
    await test_session.refresh(conn)

    assert conn.provider == "clever"
    assert conn.status == "active"
    assert conn.config_json == {"district_id": "123"}
    assert decrypt_credential(conn.credentials_encrypted) == "test-token-abc"


@pytest.mark.asyncio
async def test_sis_connection_status_transition(test_session, school_group):
    """SIS connection can transition from active to inactive."""
    conn = SISConnection(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="classlink",
        credentials_encrypted=encrypt_credential("token-xyz"),
        status="active",
    )
    test_session.add(conn)
    await test_session.flush()

    assert conn.status == "active"
    conn.status = "inactive"
    conn.credentials_encrypted = None
    await test_session.flush()

    assert conn.status == "inactive"
    assert conn.credentials_encrypted is None


@pytest.mark.asyncio
async def test_sis_connection_last_synced_update(test_session, school_group):
    """SIS connection last_synced timestamp gets updated."""
    conn = SISConnection(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="clever",
        credentials_encrypted=encrypt_credential("tok"),
        status="active",
    )
    test_session.add(conn)
    await test_session.flush()

    assert conn.last_synced is None
    now = datetime.now(timezone.utc)
    conn.last_synced = now
    await test_session.flush()
    assert conn.last_synced == now


# ---------------------------------------------------------------------------
# SSO Config model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_config_google_workspace(test_session, school_group):
    """SSO config for Google Workspace can be created."""
    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=True,
    )
    test_session.add(config)
    await test_session.flush()
    await test_session.refresh(config)

    assert config.provider == "google_workspace"
    assert config.tenant_id == "school.edu"
    assert config.auto_provision_members is True


@pytest.mark.asyncio
async def test_sso_config_microsoft_entra(test_session, school_group):
    """SSO config for Microsoft Entra can be created."""
    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="microsoft_entra",
        tenant_id="tenant-abc-123",
        auto_provision_members=False,
    )
    test_session.add(config)
    await test_session.flush()
    await test_session.refresh(config)

    assert config.provider == "microsoft_entra"
    assert config.tenant_id == "tenant-abc-123"
    assert config.auto_provision_members is False


# ---------------------------------------------------------------------------
# SIS roster sync tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_roster_creates_members(test_session, school_group):
    """sync_roster creates new group members from roster entries."""
    from src.integrations.sis_sync import sync_roster

    roster = [
        {"first_name": "Alice", "last_name": "Smith", "role": "member"},
        {"first_name": "Bob", "last_name": "Jones", "role": "member"},
    ]
    summary = await sync_roster(test_session, school_group["group"].id, roster)

    assert summary["members_created"] == 2
    assert summary["members_updated"] == 0
    assert summary["members_deactivated"] == 0


@pytest.mark.asyncio
async def test_sync_roster_updates_existing(test_session, school_group):
    """sync_roster counts existing members as updated."""
    from src.integrations.sis_sync import sync_roster

    # First create a member with matching display name
    existing = GroupMember(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        role="member",
        display_name="Alice Smith",
    )
    test_session.add(existing)
    await test_session.flush()

    roster = [
        {"first_name": "Alice", "last_name": "Smith", "role": "member"},
        {"first_name": "Charlie", "last_name": "Brown", "role": "member"},
    ]
    summary = await sync_roster(test_session, school_group["group"].id, roster)

    assert summary["members_created"] == 1  # Charlie is new
    assert summary["members_updated"] == 1  # Alice already exists


@pytest.mark.asyncio
async def test_sync_roster_empty_name_skipped(test_session, school_group):
    """sync_roster skips entries with empty names."""
    from src.integrations.sis_sync import sync_roster

    roster = [
        {"first_name": "", "last_name": "", "role": "member"},
        {"first_name": "Valid", "last_name": "Student", "role": "member"},
    ]
    summary = await sync_roster(test_session, school_group["group"].id, roster)
    assert summary["members_created"] == 1


# ---------------------------------------------------------------------------
# Auto-provisioning tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_provision_no_sso_config(test_session, school_group):
    """auto_provision_member returns None when no SSO config exists."""
    from src.integrations.sso_provisioner import auto_provision_member

    result = await auto_provision_member(
        test_session, school_group["group"].id,
        {"email": "student@school.edu", "display_name": "Student"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_auto_provision_disabled(test_session, school_group):
    """auto_provision_member returns None when auto_provision_members is False."""
    from src.integrations.sso_provisioner import auto_provision_member

    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=False,
    )
    test_session.add(config)
    await test_session.flush()

    result = await auto_provision_member(
        test_session, school_group["group"].id,
        {"email": "student@school.edu", "display_name": "Student"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_auto_provision_creates_member(test_session, school_group):
    """auto_provision_member creates a new member when enabled."""
    from src.integrations.sso_provisioner import auto_provision_member

    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=True,
    )
    test_session.add(config)
    await test_session.flush()

    result = await auto_provision_member(
        test_session, school_group["group"].id,
        {"email": "newstudent@school.edu", "display_name": "New Student"},
    )
    assert result is not None
    assert result.display_name == "New Student"
    assert result.role == "member"


@pytest.mark.asyncio
async def test_auto_provision_existing_user_returns_existing_member(test_session, school_group):
    """auto_provision_member returns existing member if user already in group."""
    from src.integrations.sso_provisioner import auto_provision_member

    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=True,
    )
    test_session.add(config)
    await test_session.flush()

    # Owner is already a member
    result = await auto_provision_member(
        test_session, school_group["group"].id,
        {"email": school_group["owner"].email, "display_name": "Existing"},
    )
    # Should return the existing member, not create a duplicate
    assert result is not None
    assert result.user_id == school_group["owner"].id


@pytest.mark.asyncio
async def test_auto_provision_no_email(test_session, school_group):
    """auto_provision_member returns None with missing email."""
    from src.integrations.sso_provisioner import auto_provision_member

    config = SSOConfig(
        id=uuid.uuid4(),
        group_id=school_group["group"].id,
        provider="google_workspace",
        tenant_id="school.edu",
        auto_provision_members=True,
    )
    test_session.add(config)
    await test_session.flush()

    result = await auto_provision_member(
        test_session, school_group["group"].id,
        {"display_name": "No Email"},
    )
    assert result is None


# ---------------------------------------------------------------------------
# Yoti age verification tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_yoti_create_session_dev_mode():
    """Yoti session creation in test/dev mode returns stub data."""
    from src.integrations.yoti import create_age_verification_session

    result = await create_age_verification_session("member-123")
    assert "session_id" in result
    assert "url" in result
    assert "dev_session_member-123" == result["session_id"]


@pytest.mark.asyncio
async def test_yoti_get_result_dev_mode():
    """Yoti result retrieval in test/dev mode returns stub verified result."""
    from src.integrations.yoti import get_age_verification_result

    result = await get_age_verification_result("test-session-abc")
    assert result["verified"] is True
    assert result["age"] == 12
    assert result["session_id"] == "test-session-abc"


@pytest.mark.asyncio
async def test_start_age_verification_member_not_found(test_session, school_group):
    """start_age_verification raises NotFoundError for unknown member."""
    from src.integrations.age_verification import start_age_verification

    with pytest.raises(NotFoundError):
        await start_age_verification(
            test_session, school_group["group"].id, uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_start_age_verification_success(test_session, school_group):
    """start_age_verification succeeds for valid member."""
    from src.integrations.age_verification import start_age_verification

    result = await start_age_verification(
        test_session,
        school_group["group"].id,
        school_group["member"].id,
    )
    assert "session_id" in result
    assert "url" in result
