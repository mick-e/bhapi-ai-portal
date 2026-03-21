"""Security tests for parental abuse safeguards.

Validates that:
1. Trusted adult requests are NEVER visible to parents/guardians
2. Custody disputes restrict secondary guardian access
3. Privacy tiers enforce correct data boundaries
4. No privilege escalation via role manipulation
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.models import User
from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.moderation.parental_safeguards import (
    CustodyConfig,
    CustodyDisputeStatus,
    GuardianRole,
    PrivacyTier,
    TeenPrivacyConfig,
    TrustedAdultRequest,
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
async def sec_engine():
    """Create security test engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sec_session(sec_engine):
    """Create security test session."""
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def sec_family(sec_session):
    """Create a complete family for security testing."""
    parent_user = User(
        id=uuid.uuid4(),
        email=f"sec-parent-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    second_parent_user = User(
        id=uuid.uuid4(),
        email=f"sec-parent2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec Parent 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([parent_user, second_parent_user])
    await sec_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Sec Family",
        type="family",
        owner_id=parent_user.id,
        settings={},
    )
    sec_session.add(group)
    await sec_session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=parent_user.id,
        role="parent",
        display_name="Parent",
    )
    second_parent_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=second_parent_user.id,
        role="parent",
        display_name="Second Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    sec_session.add_all([parent_member, second_parent_member, child_member])
    await sec_session.flush()

    return {
        "group": group,
        "parent_user": parent_user,
        "parent_member": parent_member,
        "second_parent_user": second_parent_user,
        "second_parent_member": second_parent_member,
        "child_member": child_member,
    }


# ---------------------------------------------------------------------------
# SEC-1: Trusted adult requests NEVER visible to parents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_trusted_adult_invisible_to_primary_guardian(sec_session, sec_family):
    """Primary guardian cannot see trusted adult requests."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    await request_trusted_adult(
        sec_session, child_member_id=child.id, reason="I'm scared",
    )

    visible = await check_trusted_adult_visibility(
        sec_session, child_member_id=child.id, requester_member_id=parent.id,
    )
    assert visible is False, "Primary guardian must NOT see trusted adult requests"


@pytest.mark.asyncio
async def test_sec_trusted_adult_invisible_to_secondary_guardian(sec_session, sec_family):
    """Secondary guardian cannot see trusted adult requests."""
    child = sec_family["child_member"]
    second = sec_family["second_parent_member"]

    await add_secondary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    await request_trusted_adult(
        sec_session, child_member_id=child.id, reason="Help me",
    )

    visible = await check_trusted_adult_visibility(
        sec_session, child_member_id=child.id, requester_member_id=second.id,
    )
    assert visible is False, "Secondary guardian must NOT see trusted adult requests"


@pytest.mark.asyncio
async def test_sec_trusted_adult_never_in_visible_data(sec_session, sec_family):
    """trusted_adult_requests is ALWAYS False in parent visible data."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )

    # Check across all privacy tiers
    for tier in PrivacyTier:
        await set_teen_privacy(
            sec_session, child_member_id=child.id, privacy_tier=tier,
        )
        visibility = await get_parent_visible_data(
            sec_session, child_member_id=child.id, guardian_member_id=parent.id,
        )
        assert visibility["trusted_adult_requests"] is False, (
            f"trusted_adult_requests must be False for tier {tier}"
        )


@pytest.mark.asyncio
async def test_sec_trusted_adult_no_parent_notification(sec_session, sec_family):
    """Trusted adult request does NOT include any parent notification."""
    child = sec_family["child_member"]

    result = await request_trusted_adult(
        sec_session,
        child_member_id=child.id,
        reason="Unsafe at home",
    )
    # Result should contain private message, not parent notification
    assert "private" in result["message"].lower()
    assert "parent" not in result.get("notify", "")


# ---------------------------------------------------------------------------
# SEC-2: Custody dispute access restrictions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_custody_dispute_blocks_secondary_settings(sec_session, sec_family):
    """Custody dispute blocks secondary guardian from managing settings."""
    child = sec_family["child_member"]
    second = sec_family["second_parent_member"]

    await add_secondary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    config = await set_custody_dispute(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    assert config.can_manage_settings is False
    assert config.can_approve_contacts is False


@pytest.mark.asyncio
async def test_sec_custody_dispute_restricts_data_visibility(sec_session, sec_family):
    """During dispute, secondary guardian loses message and contact access."""
    child = sec_family["child_member"]
    second = sec_family["second_parent_member"]

    await add_secondary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    await set_custody_dispute(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    visibility = await get_parent_visible_data(
        sec_session, child_member_id=child.id, guardian_member_id=second.id,
    )
    assert visibility["messages"] is False
    assert visibility["contacts"] is False
    assert visibility["activity_detail"] is False


@pytest.mark.asyncio
async def test_sec_cannot_add_duplicate_guardian(sec_session, sec_family):
    """Cannot add the same guardian twice (prevents privilege escalation)."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    with pytest.raises(ValidationError):
        await add_secondary_guardian(
            sec_session, child_member_id=child.id, guardian_member_id=parent.id,
        )


# ---------------------------------------------------------------------------
# SEC-3: Privacy tier enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec_teen_tier_blocks_message_access(sec_session, sec_family):
    """Teen tier must block parent from reading individual messages."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    await set_teen_privacy(
        sec_session, child_member_id=child.id, privacy_tier=PrivacyTier.TEEN,
    )
    visibility = await get_parent_visible_data(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    assert visibility["messages"] is False
    assert visibility["posts"] is False
    assert visibility["activity_detail"] is False


@pytest.mark.asyncio
async def test_sec_preteen_tier_blocks_only_messages(sec_session, sec_family):
    """Preteen tier blocks messages but allows posts and contacts."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    await set_teen_privacy(
        sec_session, child_member_id=child.id, privacy_tier=PrivacyTier.PRETEEN,
    )
    visibility = await get_parent_visible_data(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    assert visibility["messages"] is False
    assert visibility["posts"] is True
    assert visibility["contacts"] is True


@pytest.mark.asyncio
async def test_sec_flagged_content_always_visible(sec_session, sec_family):
    """Safety-flagged content is visible to parents regardless of tier."""
    child = sec_family["child_member"]
    parent = sec_family["parent_member"]

    await add_primary_guardian(
        sec_session, child_member_id=child.id, guardian_member_id=parent.id,
    )
    for tier in PrivacyTier:
        await set_teen_privacy(
            sec_session, child_member_id=child.id, privacy_tier=tier,
        )
        visibility = await get_parent_visible_data(
            sec_session, child_member_id=child.id, guardian_member_id=parent.id,
        )
        assert visibility["flagged_content"] is True, (
            f"Flagged content must remain visible for tier {tier}"
        )


@pytest.mark.asyncio
async def test_sec_dispute_nonexistent_config_raises(sec_session, sec_family):
    """Setting dispute on nonexistent guardian config raises NotFoundError."""
    child = sec_family["child_member"]
    random_id = uuid.uuid4()

    with pytest.raises(NotFoundError):
        await set_custody_dispute(
            sec_session,
            child_member_id=child.id,
            guardian_member_id=random_id,
        )
