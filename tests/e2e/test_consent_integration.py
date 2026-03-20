"""Tests for consent integration — blocks capture events for underage members."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.auth.models import User
from src.capture.schemas import EventPayload
from src.capture.service import ingest_event
from src.exceptions import ForbiddenError
from src.groups.agreement import create_agreement, sign_agreement
from src.groups.consent import calculate_age, get_consent_type, requires_consent
from src.groups.models import Group, GroupMember
from src.groups.schemas import MemberAdd
from src.groups.service import add_member, check_member_consent, record_consent

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def owner(test_session):
    user = User(
        id=uuid4(),
        email="owner@consent.test",
        display_name="Parent Owner",
        account_type="family",
        password_hash="hashed",
        email_verified=True,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest.fixture
async def group(test_session, owner):
    g = Group(
        id=uuid4(),
        name="Consent Test Family",
        type="family",
        owner_id=owner.id,
        settings={},
    )
    test_session.add(g)
    await test_session.flush()
    return g


@pytest.fixture
async def admin_member(test_session, group, owner):
    m = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=owner.id,
        role="parent",
        display_name="Parent Owner",
    )
    test_session.add(m)
    await test_session.flush()
    return m


@pytest.fixture
def child_dob():
    """Date of birth for a 10-year-old (requires consent under COPPA, GDPR, LGPD)."""
    now = datetime.now(timezone.utc)
    return now.replace(year=now.year - 10, month=1, day=1)


@pytest.fixture
def adult_dob():
    """Date of birth for a 20-year-old (no consent required)."""
    now = datetime.now(timezone.utc)
    return now.replace(year=now.year - 20, month=1, day=1)


# ── Consent utility tests ────────────────────────────────────────────────────

class TestConsentUtilities:

    def test_calculate_age(self, child_dob, adult_dob):
        assert calculate_age(child_dob) == 10
        assert calculate_age(adult_dob) == 20

    def test_requires_consent_coppa(self, child_dob):
        assert requires_consent(child_dob, "us") is True

    def test_requires_consent_gdpr(self, child_dob):
        assert requires_consent(child_dob, "eu") is True

    def test_requires_consent_lgpd(self, child_dob):
        assert requires_consent(child_dob, "br") is True

    def test_no_consent_adult(self, adult_dob):
        assert requires_consent(adult_dob, "us") is False
        assert requires_consent(adult_dob, "eu") is False
        assert requires_consent(adult_dob, "br") is False

    def test_no_consent_no_dob(self):
        assert requires_consent(None, "us") is False

    def test_get_consent_type_coppa(self, child_dob):
        assert get_consent_type(child_dob, "us") == "coppa"

    def test_get_consent_type_gdpr(self, child_dob):
        assert get_consent_type(child_dob, "eu") == "gdpr"

    def test_get_consent_type_lgpd(self, child_dob):
        assert get_consent_type(child_dob, "br") == "lgpd"

    def test_get_consent_type_adult(self, adult_dob):
        assert get_consent_type(adult_dob, "us") is None

    def test_get_consent_type_15yo_us_ok(self):
        """15-year-old is above COPPA threshold in US."""
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 15)
        assert get_consent_type(dob, "us") is None

    def test_get_consent_type_15yo_eu_requires(self):
        """15-year-old is below GDPR threshold in EU."""
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 15)
        assert get_consent_type(dob, "eu") == "gdpr"


# ── Service-level consent tests ──────────────────────────────────────────────

class TestConsentWorkflow:

    @pytest.mark.asyncio
    async def test_add_child_member(self, test_session, group, owner, admin_member, child_dob):
        """Adding a child member should succeed (consent is checked at capture time)."""
        data = MemberAdd(
            display_name="Child User",
            role="member",
            date_of_birth=child_dob,
        )
        member = await add_member(test_session, group.id, owner.id, data, jurisdiction="us")
        assert member.id is not None
        assert member.date_of_birth is not None

    @pytest.mark.asyncio
    async def test_check_consent_child_no_consent(self, test_session, group, owner, admin_member, child_dob):
        """Child member without consent should return False."""
        child = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Child",
            date_of_birth=child_dob,
        )
        test_session.add(child)
        await test_session.flush()

        result = await check_member_consent(test_session, group.id, child.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_consent_adult(self, test_session, group, owner, admin_member, adult_dob):
        """Adult member should not need consent."""
        adult = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Adult",
            date_of_birth=adult_dob,
        )
        test_session.add(adult)
        await test_session.flush()

        result = await check_member_consent(test_session, group.id, adult.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_consent_no_dob(self, test_session, group, owner, admin_member):
        """Member without DOB should not need consent."""
        member = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="No DOB",
        )
        test_session.add(member)
        await test_session.flush()

        result = await check_member_consent(test_session, group.id, member.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_record_consent_enables_monitoring(self, test_session, group, owner, admin_member, child_dob):
        """Recording consent should enable monitoring (check_member_consent returns True)."""
        child = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Child",
            date_of_birth=child_dob,
        )
        test_session.add(child)
        await test_session.flush()

        # Before consent
        assert await check_member_consent(test_session, group.id, child.id) is False

        # Record consent
        consent = await record_consent(
            test_session, group.id, child.id, owner.id,
            consent_type="coppa",
            evidence="parent_checkbox_v1",
        )
        assert consent.consent_type == "coppa"
        assert consent.parent_user_id == owner.id

        # After consent
        assert await check_member_consent(test_session, group.id, child.id) is True


# ── Capture event blocking tests ──────────────────────────────────────────────

class TestCaptureConsentBlocking:

    @pytest.mark.asyncio
    async def test_capture_blocked_without_consent(self, test_session, group, owner, admin_member, child_dob):
        """Capture events should be blocked for unconsented child members."""
        child = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Child",
            date_of_birth=child_dob,
        )
        test_session.add(child)
        await test_session.flush()

        payload = EventPayload(
            group_id=group.id,
            member_id=child.id,
            platform="chatgpt",
            session_id="sess_001",
            event_type="prompt",
            timestamp=datetime.now(timezone.utc),
            content="Hello world",
        )
        with pytest.raises(ForbiddenError, match="consent required"):
            await ingest_event(test_session, payload)

    @pytest.mark.asyncio
    async def test_capture_allowed_after_consent(self, test_session, group, owner, admin_member, child_dob):
        """Capture events should succeed after consent is recorded."""
        child = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Child",
            date_of_birth=child_dob,
        )
        test_session.add(child)
        await test_session.flush()

        # Record consent
        await record_consent(
            test_session, group.id, child.id, owner.id,
            consent_type="coppa",
        )

        # COPPA 2026: Create and sign family agreement for child <13
        agreement = await create_agreement(test_session, group.id, "ages_7_10", owner.id)
        await sign_agreement(test_session, agreement.id, child.id, "Child")

        payload = EventPayload(
            group_id=group.id,
            member_id=child.id,
            platform="chatgpt",
            session_id="sess_002",
            event_type="prompt",
            timestamp=datetime.now(timezone.utc),
            content="Hello world",
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None

    @pytest.mark.asyncio
    async def test_capture_allowed_for_adult(self, test_session, group, owner, admin_member, adult_dob):
        """Adult members can have events captured without consent."""
        adult = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="Adult",
            date_of_birth=adult_dob,
        )
        test_session.add(adult)
        await test_session.flush()

        payload = EventPayload(
            group_id=group.id,
            member_id=adult.id,
            platform="gemini",
            session_id="sess_003",
            event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None

    @pytest.mark.asyncio
    async def test_capture_allowed_no_dob(self, test_session, group, owner, admin_member):
        """Members without DOB can have events captured."""
        member = GroupMember(
            id=uuid4(),
            group_id=group.id,
            user_id=None,
            role="member",
            display_name="No DOB",
        )
        test_session.add(member)
        await test_session.flush()

        payload = EventPayload(
            group_id=group.id,
            member_id=member.id,
            platform="claude",
            session_id="sess_004",
            event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None
