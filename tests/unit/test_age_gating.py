"""Unit tests for COPPA 2026 age-gating via family agreements.

Tests agreement creation, signing, and active-agreement queries which
form the foundation of the age-gating consent flow.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.groups.agreement import (
    FamilyAgreement,
    create_agreement,
    sign_agreement,
    get_active_agreement,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_session():
    """In-memory SQLite async session for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    yield session
    await session.close()
    await engine.dispose()


@pytest.fixture
async def sample_user(test_session):
    """Create a test user (group owner / parent)."""
    user = User(
        id=uuid4(),
        email=f"parent-{uuid4().hex[:8]}@example.com",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest.fixture
async def sample_group(test_session, sample_user):
    """Create a test family group owned by sample_user."""
    group = Group(
        id=uuid4(),
        name="Test Family",
        type="family",
        owner_id=sample_user.id,
        settings={},
    )
    test_session.add(group)
    await test_session.flush()
    return group


@pytest.fixture
async def sample_member(test_session, sample_group):
    """Create a child member in sample_group."""
    member = GroupMember(
        id=uuid4(),
        group_id=sample_group.id,
        user_id=None,
        role="member",
        display_name="Test Child",
    )
    test_session.add(member)
    await test_session.flush()
    return member


# ---------------------------------------------------------------------------
# Active agreement lookup (age-gating prerequisite)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetActiveAgreement:
    """Tests for get_active_agreement() — the first half of age-gating check."""

    async def test_returns_none_no_agreement(self, test_session, sample_group):
        """No agreement exists -> returns None."""
        result = await get_active_agreement(test_session, sample_group.id)
        assert result is None

    async def test_returns_none_wrong_group(self, test_session):
        """Agreement in different group -> returns None."""
        result = await get_active_agreement(test_session, uuid4())
        assert result is None

    async def test_returns_active_agreement(self, test_session, sample_group, sample_user):
        """Active agreement exists -> returns it."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()

        result = await get_active_agreement(test_session, sample_group.id)
        assert result is not None
        assert result.id == agreement.id
        assert result.active is True

    async def test_inactive_agreement_not_returned(self, test_session, sample_group, sample_user):
        """Deactivated agreement is not returned."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        agreement.active = False
        await test_session.flush()
        await test_session.commit()

        result = await get_active_agreement(test_session, sample_group.id)
        assert result is None


# ---------------------------------------------------------------------------
# Agreement signing (member consent for age-gating)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSignAgreement:
    """Tests for sign_agreement() — member signs the family agreement."""

    async def test_member_can_sign(self, test_session, sample_group, sample_member, sample_user):
        """Member signs agreement -> appears in signed_by_members."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()

        signed = await sign_agreement(
            test_session, agreement.id, sample_member.id, "Test Child"
        )
        assert len(signed.signed_by_members) == 1
        assert signed.signed_by_members[0]["member_id"] == str(sample_member.id)
        assert signed.signed_by_members[0]["name"] == "Test Child"

    async def test_unsigned_member_not_in_list(self, test_session, sample_group, sample_user):
        """Unsigned member does not appear in signed_by_members."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()

        assert len(agreement.signed_by_members) == 0

    async def test_duplicate_signature_raises(self, test_session, sample_group, sample_member, sample_user):
        """Signing twice raises ConflictError."""
        from src.exceptions import ConflictError

        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()

        await sign_agreement(test_session, agreement.id, sample_member.id, "Test Child")
        await test_session.commit()

        with pytest.raises(ConflictError):
            await sign_agreement(test_session, agreement.id, sample_member.id, "Test Child")

    async def test_wrong_member_not_signed(self, test_session, sample_group, sample_member, sample_user):
        """Agreement exists but different member signed -> original member absent."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()

        other_member_id = uuid4()
        await sign_agreement(test_session, agreement.id, other_member_id, "Other Child")
        await test_session.commit()

        # Verify sample_member is NOT in the signed list
        signed_ids = [s["member_id"] for s in agreement.signed_by_members]
        assert str(sample_member.id) not in signed_ids


# ---------------------------------------------------------------------------
# Agreement creation with templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateAgreement:
    """Tests for create_agreement() — age-appropriate templates."""

    async def test_creates_with_template_rules(self, test_session, sample_group, sample_user):
        """Agreement is created with rules from the template."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        assert agreement.template_id == "ages_7_10"
        assert len(agreement.rules) > 0
        assert agreement.active is True

    async def test_sets_review_due(self, test_session, sample_group, sample_user):
        """Agreement has a review_due date set ~90 days from creation."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_11_13", sample_user.id
        )
        today = date.today()
        assert agreement.review_due >= today + timedelta(days=89)
        assert agreement.review_due <= today + timedelta(days=91)

    async def test_invalid_template_raises(self, test_session, sample_group, sample_user):
        """Invalid template_id raises ValidationError."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await create_agreement(
                test_session, sample_group.id, "nonexistent_template", sample_user.id
            )

    async def test_new_agreement_deactivates_old(self, test_session, sample_group, sample_user):
        """Creating a new agreement deactivates the previous one."""
        first = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        await test_session.commit()
        first_id = first.id

        second = await create_agreement(
            test_session, sample_group.id, "ages_11_13", sample_user.id
        )
        await test_session.commit()

        # Refresh first to see updated state
        await test_session.refresh(first)
        assert first.active is False
        assert second.active is True

    async def test_parent_is_recorded_as_signer(self, test_session, sample_group, sample_user):
        """Parent who creates the agreement is recorded as initial signer."""
        agreement = await create_agreement(
            test_session, sample_group.id, "ages_7_10", sample_user.id
        )
        assert agreement.signed_by_parent == sample_user.id
        assert agreement.signed_by_parent_at is not None
