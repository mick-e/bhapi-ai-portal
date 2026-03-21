"""End-to-end tests for parental abuse safeguards API."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# Import models to register them with Base.metadata before create_all
from src.moderation.parental_safeguards import (  # noqa: F401
    CustodyConfig,
    TeenPrivacyConfig,
    TrustedAdultRequest,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    """Create E2E test engine."""
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
async def e2e_session(e2e_engine):
    """Create E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def parent_user(e2e_session):
    """Create a parent user."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-parent-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def child_user(e2e_session):
    """Create a child user."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-child-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def family_group(e2e_session, parent_user):
    """Create a family group."""
    group = Group(
        id=uuid.uuid4(),
        name="E2E Family",
        type="family",
        owner_id=parent_user.id,
        settings={},
    )
    e2e_session.add(group)
    await e2e_session.flush()
    return group


@pytest_asyncio.fixture
async def parent_member(e2e_session, family_group, parent_user):
    """Create parent group member."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=parent_user.id,
        role="parent",
        display_name="Parent",
    )
    e2e_session.add(member)
    await e2e_session.flush()
    return member


@pytest_asyncio.fixture
async def child_member(e2e_session, family_group, child_user):
    """Create child group member."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=child_user.id,
        role="member",
        display_name="Child",
    )
    e2e_session.add(member)
    await e2e_session.flush()
    return member


def _make_client(engine, session, user, group_id=None, role=None):
    """Create an authed client for API tests."""
    app = create_app()

    async def override_get_db():
        yield session

    async def override_get_current_user():
        return GroupContext(
            user_id=user.id,
            group_id=group_id,
            role=role or "parent",
            permissions=["*"],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Trusted Adult API Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_trusted_adult_e2e(
    e2e_engine, e2e_session, child_user, child_member, family_group,
):
    """Child can request a trusted adult via the service layer."""
    from src.moderation.parental_safeguards import request_trusted_adult

    result = await request_trusted_adult(
        e2e_session,
        child_member_id=child_member.id,
        trusted_adult_name="Uncle Bob",
        trusted_adult_contact="bob@example.com",
        reason="I need someone to talk to",
    )
    assert result["status"] == "pending"
    assert "helplines" in result
    assert "private" in result["message"].lower()


@pytest.mark.asyncio
async def test_trusted_adult_not_in_parent_data_e2e(
    e2e_engine, e2e_session, parent_user, parent_member,
    child_user, child_member, family_group,
):
    """Parent cannot see trusted adult requests in visible data."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
        request_trusted_adult,
    )

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    await request_trusted_adult(
        e2e_session,
        child_member_id=child_member.id,
        reason="Help needed",
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["trusted_adult_requests"] is False


@pytest.mark.asyncio
async def test_helplines_by_jurisdiction_e2e(e2e_session, child_member):
    """Different jurisdictions return different helplines."""
    from src.moderation.parental_safeguards import request_trusted_adult

    us = await request_trusted_adult(
        e2e_session, child_member_id=child_member.id, jurisdiction="US",
    )
    assert any("Childhelp" in h["name"] for h in us["helplines"])

    # Create a new child member for AU test (avoid uniqueness issues)
    au_child = GroupMember(
        id=uuid.uuid4(),
        group_id=child_member.group_id,
        user_id=None,
        role="member",
        display_name="AU Child",
    )
    e2e_session.add(au_child)
    await e2e_session.flush()

    au = await request_trusted_adult(
        e2e_session, child_member_id=au_child.id, jurisdiction="AU",
    )
    assert any("Kids Helpline" in h["name"] for h in au["helplines"])


# ---------------------------------------------------------------------------
# Custody E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_primary_guardian_full_access_e2e(
    e2e_engine, e2e_session, parent_member, child_member,
):
    """Primary guardian gets full access."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
    )

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is True
    assert visibility["messages"] is True
    assert visibility["contacts"] is True


@pytest.mark.asyncio
async def test_secondary_guardian_limited_e2e(
    e2e_engine, e2e_session, child_member, family_group,
):
    """Secondary guardian with restricted permissions."""
    from src.moderation.parental_safeguards import (
        add_secondary_guardian,
        get_guardian_access,
    )

    second_user = User(
        id=uuid.uuid4(),
        email=f"second-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Second Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(second_user)
    await e2e_session.flush()

    second_member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=second_user.id,
        role="parent",
        display_name="Second Parent",
    )
    e2e_session.add(second_member)
    await e2e_session.flush()

    await add_secondary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=second_member.id,
    )
    config = await get_guardian_access(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=second_member.id,
    )
    assert config.can_manage_settings is False
    assert config.can_approve_contacts is False


@pytest.mark.asyncio
async def test_custody_dispute_restricts_secondary_e2e(
    e2e_engine, e2e_session, child_member, family_group,
):
    """Custody dispute restricts secondary guardian access."""
    from src.moderation.parental_safeguards import (
        add_secondary_guardian,
        get_parent_visible_data,
        set_custody_dispute,
    )

    second_user = User(
        id=uuid.uuid4(),
        email=f"sec-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(second_user)
    await e2e_session.flush()

    sec_member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=second_user.id,
        role="parent",
        display_name="Sec Parent",
    )
    e2e_session.add(sec_member)
    await e2e_session.flush()

    await add_secondary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
    )
    await set_custody_dispute(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
        notes="Court proceeding active",
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
    )
    assert visibility["messages"] is False
    assert visibility["contacts"] is False


@pytest.mark.asyncio
async def test_custody_dispute_resolve_e2e(
    e2e_engine, e2e_session, child_member, family_group,
):
    """Resolving custody dispute updates status."""
    from src.moderation.parental_safeguards import (
        add_secondary_guardian,
        resolve_custody_dispute,
        set_custody_dispute,
    )

    sec_user = User(
        id=uuid.uuid4(),
        email=f"res-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Res Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(sec_user)
    await e2e_session.flush()

    sec_member = GroupMember(
        id=uuid.uuid4(),
        group_id=family_group.id,
        user_id=sec_user.id,
        role="parent",
        display_name="Res Parent",
    )
    e2e_session.add(sec_member)
    await e2e_session.flush()

    await add_secondary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
    )
    await set_custody_dispute(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
    )
    config = await resolve_custody_dispute(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=sec_member.id,
    )
    assert config.dispute_status == "resolved"


# ---------------------------------------------------------------------------
# Teen Privacy E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_tier_full_visibility_e2e(e2e_session, child_member, parent_member):
    """Young tier gives parent full visibility."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
        set_teen_privacy,
    )
    from src.moderation.parental_safeguards import PrivacyTier

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    await set_teen_privacy(
        e2e_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.YOUNG,
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is True
    assert visibility["messages"] is True
    assert visibility["contacts"] is True


@pytest.mark.asyncio
async def test_preteen_tier_no_messages_e2e(e2e_session, child_member, parent_member):
    """Preteen tier hides messages from parent."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
        set_teen_privacy,
    )
    from src.moderation.parental_safeguards import PrivacyTier

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    await set_teen_privacy(
        e2e_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.PRETEEN,
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is True
    assert visibility["contacts"] is True
    assert visibility["messages"] is False


@pytest.mark.asyncio
async def test_teen_tier_summary_only_e2e(e2e_session, child_member, parent_member):
    """Teen tier shows only summary and flagged content."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
        set_teen_privacy,
    )
    from src.moderation.parental_safeguards import PrivacyTier

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    await set_teen_privacy(
        e2e_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.TEEN,
    )
    visibility = await get_parent_visible_data(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    assert visibility["posts"] is False
    assert visibility["messages"] is False
    assert visibility["activity_detail"] is False
    assert visibility["activity_summary"] is True
    assert visibility["flagged_content"] is True


@pytest.mark.asyncio
async def test_privacy_tier_upgrade_e2e(e2e_session, child_member):
    """Privacy tier can be upgraded from young to teen."""
    from src.moderation.parental_safeguards import set_teen_privacy
    from src.moderation.parental_safeguards import PrivacyTier

    config = await set_teen_privacy(
        e2e_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.YOUNG,
    )
    assert config.messages_visible is True

    config = await set_teen_privacy(
        e2e_session,
        child_member_id=child_member.id,
        privacy_tier=PrivacyTier.TEEN,
    )
    assert config.messages_visible is False
    assert config.activity_summary_only is True


@pytest.mark.asyncio
async def test_multiple_children_independent_privacy_e2e(
    e2e_session, family_group, parent_member,
):
    """Each child can have independent privacy settings."""
    from src.moderation.parental_safeguards import (
        add_primary_guardian,
        get_parent_visible_data,
        set_teen_privacy,
    )
    from src.moderation.parental_safeguards import PrivacyTier

    child1 = GroupMember(
        id=uuid.uuid4(), group_id=family_group.id, user_id=None,
        role="member", display_name="Child 1",
    )
    child2 = GroupMember(
        id=uuid.uuid4(), group_id=family_group.id, user_id=None,
        role="member", display_name="Child 2",
    )
    e2e_session.add_all([child1, child2])
    await e2e_session.flush()

    await add_primary_guardian(
        e2e_session, child_member_id=child1.id, guardian_member_id=parent_member.id,
    )
    await add_primary_guardian(
        e2e_session, child_member_id=child2.id, guardian_member_id=parent_member.id,
    )
    await set_teen_privacy(
        e2e_session, child_member_id=child1.id, privacy_tier=PrivacyTier.YOUNG,
    )
    await set_teen_privacy(
        e2e_session, child_member_id=child2.id, privacy_tier=PrivacyTier.TEEN,
    )

    vis1 = await get_parent_visible_data(
        e2e_session, child_member_id=child1.id, guardian_member_id=parent_member.id,
    )
    vis2 = await get_parent_visible_data(
        e2e_session, child_member_id=child2.id, guardian_member_id=parent_member.id,
    )
    assert vis1["messages"] is True
    assert vis2["messages"] is False


@pytest.mark.asyncio
async def test_default_helpline_jurisdiction_e2e(e2e_session, child_member):
    """Unknown jurisdiction falls back to DEFAULT helplines."""
    from src.moderation.parental_safeguards import request_trusted_adult

    result = await request_trusted_adult(
        e2e_session, child_member_id=child_member.id, jurisdiction="ZZ",
    )
    assert len(result["helplines"]) > 0
    assert any("Crisis Text Line" in h["name"] for h in result["helplines"])


@pytest.mark.asyncio
async def test_secondary_guardian_custom_permissions_e2e(
    e2e_session, child_member, family_group,
):
    """Secondary guardian can have custom view + approve permissions."""
    from src.moderation.parental_safeguards import add_secondary_guardian, get_guardian_access

    custom_user = User(
        id=uuid.uuid4(),
        email=f"custom-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Custom Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(custom_user)
    await e2e_session.flush()

    custom_member = GroupMember(
        id=uuid.uuid4(), group_id=family_group.id,
        user_id=custom_user.id, role="parent", display_name="Custom Parent",
    )
    e2e_session.add(custom_member)
    await e2e_session.flush()

    config = await add_secondary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=custom_member.id,
        can_view_activity=True,
        can_manage_settings=False,
        can_approve_contacts=True,
    )
    assert config.can_view_activity is True
    assert config.can_manage_settings is False
    assert config.can_approve_contacts is True


@pytest.mark.asyncio
async def test_duplicate_guardian_blocked_e2e(e2e_session, child_member, parent_member):
    """Cannot add the same guardian twice."""
    from src.moderation.parental_safeguards import add_primary_guardian
    from src.exceptions import ValidationError

    await add_primary_guardian(
        e2e_session,
        child_member_id=child_member.id,
        guardian_member_id=parent_member.id,
    )
    with pytest.raises(ValidationError):
        await add_primary_guardian(
            e2e_session,
            child_member_id=child_member.id,
            guardian_member_id=parent_member.id,
        )
