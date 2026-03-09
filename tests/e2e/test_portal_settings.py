"""E2E tests for portal settings GET/PATCH service functions.

Covers get_group_settings (defaults, stored values, 404) and
update_group_settings (name, safety_level, notifications, budget, admin role).
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.models import User
from src.billing.models import BudgetThreshold
from src.database import Base
from src.exceptions import ForbiddenError, NotFoundError
from src.groups.models import Group, GroupMember
from src.portal.schemas import GroupSettingsResponse, UpdateGroupSettingsRequest
from src.portal.service import get_group_settings, update_group_settings

# ---------------------------------------------------------------------------
# Fixture: async session with in-memory SQLite
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    """Create an in-memory SQLite database and yield an AsyncSession."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    user_id=None,
    email="admin@family.test",
    display_name="Admin User",
    account_type="family",
):
    """Return a User model instance."""
    return User(
        id=user_id or uuid4(),
        email=email,
        display_name=display_name,
        account_type=account_type,
        password_hash="hashed",
        email_verified=True,
    )


def _make_group(owner_id, group_id=None, name="Test Family", group_type="family", settings=None):
    """Return a Group model instance."""
    return Group(
        id=group_id or uuid4(),
        name=name,
        type=group_type,
        owner_id=owner_id,
        settings=settings if settings is not None else {},
    )


def _make_member(group_id, user_id, role="parent", display_name="Admin User", member_id=None):
    """Return a GroupMember model instance."""
    return GroupMember(
        id=member_id or uuid4(),
        group_id=group_id,
        user_id=user_id,
        role=role,
        display_name=display_name,
    )


# ---------------------------------------------------------------------------
# 1. get_group_settings returns correct defaults
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_group_settings_returns_defaults(db):
    """get_group_settings returns GroupSettingsResponse with default values
    when the group has an empty settings dict."""
    user = _make_user()
    group = _make_group(owner_id=user.id)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    result = await get_group_settings(db, group.id, user.id)

    assert isinstance(result, GroupSettingsResponse)
    assert result.group_id == group.id
    assert result.group_name == "Test Family"
    assert result.account_type == "family"
    assert result.safety_level == "strict"
    assert result.auto_block_critical is True
    assert result.prompt_logging is True
    assert result.pii_detection is True
    assert result.monthly_budget_usd == 0.0
    assert result.plan == "free"
    # Default notification preferences — all True
    assert result.notifications.critical_safety is True
    assert result.notifications.risk_warnings is True
    assert result.notifications.spend_alerts is True
    assert result.notifications.member_updates is True
    assert result.notifications.weekly_digest is True
    assert result.notifications.report_notifications is True


# ---------------------------------------------------------------------------
# 2. get_group_settings returns stored values
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_group_settings_returns_stored_values(db):
    """get_group_settings returns values stored in group.settings JSON."""
    user = _make_user(email="stored@family.test")
    stored_settings = {
        "safety_level": "moderate",
        "auto_block_critical": False,
        "prompt_logging": False,
        "pii_detection": False,
        "plan": "family",
        "notifications": {
            "critical_safety": True,
            "risk_warnings": False,
            "spend_alerts": True,
            "member_updates": False,
            "weekly_digest": False,
            "report_notifications": True,
        },
    }
    group = _make_group(owner_id=user.id, name="Stored Family", settings=stored_settings)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    result = await get_group_settings(db, group.id, user.id)

    assert result.safety_level == "moderate"
    assert result.auto_block_critical is False
    assert result.prompt_logging is False
    assert result.pii_detection is False
    # plan is now derived from subscription/trial status, not settings JSON
    assert result.plan == "free"
    assert result.notifications.critical_safety is True
    assert result.notifications.risk_warnings is False
    assert result.notifications.spend_alerts is True
    assert result.notifications.member_updates is False
    assert result.notifications.weekly_digest is False
    assert result.notifications.report_notifications is True


# ---------------------------------------------------------------------------
# 3. update_group_settings changes group name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_changes_name(db):
    """update_group_settings updates the group name."""
    user = _make_user(email="rename@family.test")
    group = _make_group(owner_id=user.id, name="Old Name")
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    request = UpdateGroupSettingsRequest(group_name="New Family Name")
    result = await update_group_settings(db, group.id, user.id, request)

    assert result.group_name == "New Family Name"


# ---------------------------------------------------------------------------
# 4. update_group_settings changes safety_level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_changes_safety_level(db):
    """update_group_settings updates the safety_level setting."""
    user = _make_user(email="safety@family.test")
    group = _make_group(owner_id=user.id)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    request = UpdateGroupSettingsRequest(safety_level="moderate")
    result = await update_group_settings(db, group.id, user.id, request)

    assert result.safety_level == "moderate"

    # Verify persistence by re-reading
    fresh = await get_group_settings(db, group.id, user.id)
    assert fresh.safety_level == "moderate"


# ---------------------------------------------------------------------------
# 5. update_group_settings changes notification preferences
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_changes_notifications(db):
    """update_group_settings updates notification preferences."""
    user = _make_user(email="notif@family.test")
    group = _make_group(owner_id=user.id)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    request = UpdateGroupSettingsRequest(
        notifications={
            "critical_safety": True,
            "risk_warnings": False,
            "spend_alerts": False,
            "member_updates": True,
            "weekly_digest": False,
            "report_notifications": False,
        }
    )
    result = await update_group_settings(db, group.id, user.id, request)

    assert result.notifications.critical_safety is True
    assert result.notifications.risk_warnings is False
    assert result.notifications.spend_alerts is False
    assert result.notifications.member_updates is True
    assert result.notifications.weekly_digest is False
    assert result.notifications.report_notifications is False


# ---------------------------------------------------------------------------
# 6. update_group_settings creates budget threshold when none exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_creates_budget(db):
    """update_group_settings creates a BudgetThreshold when none exists."""
    user = _make_user(email="budget-new@family.test")
    group = _make_group(owner_id=user.id)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    # Verify no budget yet
    initial = await get_group_settings(db, group.id, user.id)
    assert initial.monthly_budget_usd == 0.0

    request = UpdateGroupSettingsRequest(monthly_budget_usd=75.0)
    result = await update_group_settings(db, group.id, user.id, request)

    assert result.monthly_budget_usd == 75.0


# ---------------------------------------------------------------------------
# 7. update_group_settings updates existing budget threshold
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_updates_existing_budget(db):
    """update_group_settings updates an existing BudgetThreshold amount."""
    user = _make_user(email="budget-upd@family.test")
    group = _make_group(owner_id=user.id)
    member = _make_member(group.id, user.id)
    db.add_all([user, group, member])
    await db.commit()

    existing_budget = BudgetThreshold(
        id=uuid4(),
        group_id=group.id,
        member_id=None,
        amount=50.0,
        currency="USD",
        type="hard",
    )
    db.add(existing_budget)
    await db.commit()

    # Confirm current budget
    before = await get_group_settings(db, group.id, user.id)
    assert before.monthly_budget_usd == 50.0

    request = UpdateGroupSettingsRequest(monthly_budget_usd=150.0)
    result = await update_group_settings(db, group.id, user.id, request)

    assert result.monthly_budget_usd == 150.0


# ---------------------------------------------------------------------------
# 8. update_group_settings requires admin role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_group_settings_requires_admin_role(db):
    """update_group_settings raises ForbiddenError for non-admin members."""
    admin_user = _make_user(email="admin@family.test")
    regular_user = _make_user(email="member@family.test", display_name="Regular User")
    group = _make_group(owner_id=admin_user.id)
    admin_member = _make_member(group.id, admin_user.id, role="parent")
    regular_member = _make_member(
        group.id, regular_user.id, role="member", display_name="Regular User"
    )
    db.add_all([admin_user, regular_user, group, admin_member, regular_member])
    await db.commit()

    request = UpdateGroupSettingsRequest(group_name="Hacked Name")

    with pytest.raises(ForbiddenError):
        await update_group_settings(db, group.id, regular_user.id, request)


# ---------------------------------------------------------------------------
# 9. get_group_settings returns 404 for non-existent group
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_group_settings_not_found(db):
    """get_group_settings raises NotFoundError for a non-existent group."""
    non_existent_group_id = uuid4()
    user_id = uuid4()

    with pytest.raises(NotFoundError):
        await get_group_settings(db, non_existent_group_id, user_id)
