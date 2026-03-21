"""Unit tests for anti-abuse detection — age misrepresentation, account farming,
coordinated harassment, report abuse, invitation rate, content manipulation.

Target: 30+ unit tests.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.age_tier.rules import AgeTier
from src.auth.models import User
from src.contacts.models import Contact
from src.device_agent.models import DeviceSession
from src.groups.models import GroupMember
from src.intelligence.models import AbuseSignal
from src.moderation.anti_abuse import (
    INVITATION_LIMITS,
    AbuseType,
    _compute_vocabulary_complexity,
    _is_curfew_violation,
    check_content_manipulation,
    check_invitation_rate,
    detect_account_farming,
    detect_age_misrepresentation,
    detect_coordinated_harassment,
    detect_report_abuse,
    normalize_homoglyphs,
    normalize_leetspeak,
    record_abuse_signal,
)
from src.moderation.models import ContentReport
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_member(session, group, name="Child") -> tuple[GroupMember, User]:
    """Create a User + GroupMember linked together."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"test-{uuid4().hex[:8]}@example.com",
        display_name=name,
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=user_id,
        role="member",
        display_name=name,
    )
    session.add(member)
    await session.flush()
    return member, user


# ===========================================================================
# 1. Age Misrepresentation Tests
# ===========================================================================


class TestDetectAgeMisrepresentation:
    """Tests for detect_age_misrepresentation."""

    def test_young_tier_simple_vocabulary_no_flag(self):
        """Young tier with simple words should not flag."""
        result = detect_age_misrepresentation(
            text="I like cats and dogs and fun toys",
            post_times=[datetime(2026, 3, 21, 14, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is False
        assert result["severity"] == "low"

    def test_young_tier_complex_vocabulary_flags(self):
        """Young tier with advanced vocabulary should flag."""
        result = detect_age_misrepresentation(
            text="The philosophical implications of quantum mechanics are extraordinary",
            post_times=[datetime(2026, 3, 21, 14, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is True
        assert result["vocabulary_complexity"] > 5.0
        assert any("Vocabulary" in s for s in result["signals"])

    def test_young_tier_curfew_violation(self):
        """Young tier posting at 11 PM should flag curfew."""
        result = detect_age_misrepresentation(
            text="hi there",
            post_times=[datetime(2026, 3, 21, 23, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is True
        assert result["curfew_violations"] == 1
        assert any("curfew" in s for s in result["signals"])

    def test_young_tier_both_signals_high_severity(self):
        """Both vocabulary + curfew = high severity."""
        result = detect_age_misrepresentation(
            text="Sophisticated algorithmic transformations demonstrate unprecedented capability",
            post_times=[datetime(2026, 3, 21, 23, 30, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is True
        assert result["severity"] == "high"
        assert len(result["signals"]) >= 2

    def test_preteen_tier_moderate_vocabulary_no_flag(self):
        """Preteen tier with moderate words should not flag."""
        result = detect_age_misrepresentation(
            text="Today I played soccer after school with friends",
            post_times=[datetime(2026, 3, 21, 16, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.PRETEEN,
        )
        assert result["flagged"] is False

    def test_preteen_curfew_11pm_flags(self):
        """Preteen posting at 11 PM should flag curfew."""
        result = detect_age_misrepresentation(
            text="hello",
            post_times=[datetime(2026, 3, 21, 23, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.PRETEEN,
        )
        assert result["curfew_violations"] == 1
        assert result["flagged"] is True

    def test_preteen_curfew_9pm_no_flag(self):
        """Preteen posting at 9 PM should NOT flag curfew."""
        result = detect_age_misrepresentation(
            text="hello",
            post_times=[datetime(2026, 3, 21, 21, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.PRETEEN,
        )
        assert result["curfew_violations"] == 0

    def test_teen_no_curfew(self):
        """Teen posting at midnight should not trigger curfew."""
        result = detect_age_misrepresentation(
            text="hello world",
            post_times=[datetime(2026, 3, 22, 0, 30, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.TEEN,
        )
        assert result["curfew_violations"] == 0

    def test_empty_text_returns_zero_complexity(self):
        """Empty text should return 0 complexity and no flag."""
        result = detect_age_misrepresentation(
            text="",
            post_times=[],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["vocabulary_complexity"] == 0.0
        assert result["flagged"] is False

    def test_multiple_curfew_violations(self):
        """Multiple late-night posts should count correctly."""
        times = [
            datetime(2026, 3, 21, 22, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 21, 23, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 22, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 22, 10, 0, tzinfo=timezone.utc),  # not curfew
        ]
        result = detect_age_misrepresentation(
            text="hi",
            post_times=times,
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["curfew_violations"] == 3


# ===========================================================================
# 2. Vocabulary Complexity Helper
# ===========================================================================


class TestVocabularyComplexity:
    """Tests for _compute_vocabulary_complexity."""

    def test_simple_words(self):
        assert _compute_vocabulary_complexity("I am a cat") == pytest.approx(1.75, abs=0.1)

    def test_long_words(self):
        val = _compute_vocabulary_complexity("extraordinary philosophical implications")
        assert val > 7.0

    def test_empty_string(self):
        assert _compute_vocabulary_complexity("") == 0.0

    def test_numbers_ignored(self):
        """Non-alpha chars are stripped; only words counted."""
        val = _compute_vocabulary_complexity("123 hello 456")
        assert val == 5.0


# ===========================================================================
# 3. Curfew Violation Helper
# ===========================================================================


class TestCurfewViolation:
    """Tests for _is_curfew_violation."""

    def test_young_8pm_is_curfew(self):
        t = datetime(2026, 3, 21, 20, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.YOUNG) is True

    def test_young_3am_is_curfew(self):
        t = datetime(2026, 3, 21, 3, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.YOUNG) is True

    def test_young_noon_ok(self):
        t = datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.YOUNG) is False

    def test_preteen_10pm_is_curfew(self):
        t = datetime(2026, 3, 21, 22, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.PRETEEN) is True

    def test_preteen_9pm_ok(self):
        t = datetime(2026, 3, 21, 21, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.PRETEEN) is False

    def test_teen_midnight_ok(self):
        t = datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc)
        assert _is_curfew_violation(t, AgeTier.TEEN) is False


# ===========================================================================
# 4. Account Farming Tests (DB-backed)
# ===========================================================================


class TestDetectAccountFarming:
    """Tests for detect_account_farming."""

    @pytest.mark.asyncio
    async def test_single_account_no_flag(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group)

        session = DeviceSession(
            id=uuid4(),
            member_id=member.id,
            group_id=group.id,
            device_id="device-abc-123",
            device_type="ios",
            started_at=datetime.now(timezone.utc),
        )
        test_session.add(session)
        await test_session.flush()

        result = await detect_account_farming(test_session, "device-abc-123")
        assert result["flagged"] is False
        assert result["account_count"] == 1

    @pytest.mark.asyncio
    async def test_four_accounts_flags(self, test_session):
        group, owner_id = await make_test_group(test_session)
        device_id = "farm-device-001"

        for i in range(4):
            member, _ = await _make_member(test_session, group, f"Farm{i}")
            session = DeviceSession(
                id=uuid4(),
                member_id=member.id,
                group_id=group.id,
                device_id=device_id,
                device_type="android",
                started_at=datetime.now(timezone.utc),
            )
            test_session.add(session)
        await test_session.flush()

        result = await detect_account_farming(test_session, device_id)
        assert result["flagged"] is True
        assert result["account_count"] == 4
        assert result["severity"] == "high"

    @pytest.mark.asyncio
    async def test_old_sessions_excluded(self, test_session):
        """Sessions older than window_days should not count."""
        group, owner_id = await make_test_group(test_session)
        device_id = "old-device-001"
        old_time = datetime.now(timezone.utc) - timedelta(days=60)

        for i in range(5):
            member, _ = await _make_member(test_session, group, f"Old{i}")
            session = DeviceSession(
                id=uuid4(),
                member_id=member.id,
                group_id=group.id,
                device_id=device_id,
                device_type="ios",
                started_at=old_time,
            )
            test_session.add(session)
        await test_session.flush()

        result = await detect_account_farming(test_session, device_id)
        assert result["flagged"] is False
        assert result["account_count"] == 0

    @pytest.mark.asyncio
    async def test_critical_severity_many_accounts(self, test_session):
        """More than 6 accounts = critical severity."""
        group, _ = await make_test_group(test_session)
        device_id = "mass-farm-device"

        for i in range(7):
            member, _ = await _make_member(test_session, group, f"Mass{i}")
            test_session.add(DeviceSession(
                id=uuid4(),
                member_id=member.id,
                group_id=group.id,
                device_id=device_id,
                device_type="android",
                started_at=datetime.now(timezone.utc),
            ))
        await test_session.flush()

        result = await detect_account_farming(test_session, device_id)
        assert result["severity"] == "critical"


# ===========================================================================
# 5. Coordinated Harassment Tests (DB-backed)
# ===========================================================================


class TestDetectCoordinatedHarassment:
    """Tests for detect_coordinated_harassment."""

    @pytest.mark.asyncio
    async def test_no_reports_no_flag(self, test_session):
        target_id = uuid4()
        result = await detect_coordinated_harassment(test_session, target_id)
        assert result["flagged"] is False
        assert result["reporter_count"] == 0

    @pytest.mark.asyncio
    async def test_three_reporters_flags(self, test_session):
        group, _ = await make_test_group(test_session)
        target_id = uuid4()

        for i in range(3):
            _, user = await _make_member(test_session, group, f"Reporter{i}")
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="user",
                target_id=target_id,
                reason="bullying",
                status="pending",
            ))
        await test_session.flush()

        result = await detect_coordinated_harassment(test_session, target_id)
        assert result["flagged"] is True
        assert result["reporter_count"] >= 3

    @pytest.mark.asyncio
    async def test_same_reporter_multiple_reports_not_flagged(self, test_session):
        """A single reporter filing many reports should not trigger harassment."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "SingleReporter")
        target_id = uuid4()

        for _ in range(5):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="user",
                target_id=target_id,
                reason="spam",
                status="pending",
            ))
        await test_session.flush()

        result = await detect_coordinated_harassment(test_session, target_id)
        assert result["flagged"] is False
        assert result["reporter_count"] == 1
        assert result["report_count"] == 5


# ===========================================================================
# 6. Report Abuse Tests (DB-backed)
# ===========================================================================


class TestDetectReportAbuse:
    """Tests for detect_report_abuse."""

    @pytest.mark.asyncio
    async def test_few_reports_no_flag(self, test_session):
        """Under minimum threshold, never flag."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "FewReports")

        for i in range(3):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="post",
                target_id=uuid4(),
                reason="spam",
                status="dismissed",
            ))
        await test_session.flush()

        result = await detect_report_abuse(test_session, user.id)
        assert result["flagged"] is False
        assert result["total_reports"] == 3

    @pytest.mark.asyncio
    async def test_high_dismiss_rate_flags(self, test_session):
        """80%+ dismissed reports should flag."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "Abuser")

        # 5 reports, 4 dismissed, 1 action_taken
        for i in range(4):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="post",
                target_id=uuid4(),
                reason="spam",
                status="dismissed",
            ))
        test_session.add(ContentReport(
            id=uuid4(),
            reporter_id=user.id,
            target_type="post",
            target_id=uuid4(),
            reason="spam",
            status="action_taken",
        ))
        await test_session.flush()

        result = await detect_report_abuse(test_session, user.id)
        assert result["flagged"] is True
        assert result["dismiss_rate"] == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_low_dismiss_rate_no_flag(self, test_session):
        """50% dismiss rate should not flag."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "Honest")

        for i in range(5):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="post",
                target_id=uuid4(),
                reason="bullying",
                status="dismissed" if i < 2 else "action_taken",
            ))
        # Need 1 more to reach min threshold of 5
        await test_session.flush()

        result = await detect_report_abuse(test_session, user.id)
        assert result["flagged"] is False
        assert result["dismiss_rate"] == pytest.approx(0.4)


# ===========================================================================
# 7. Invitation Rate Limit Tests (DB-backed)
# ===========================================================================


class TestCheckInvitationRate:
    """Tests for check_invitation_rate."""

    @pytest.mark.asyncio
    async def test_young_under_limit_allowed(self, test_session):
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "YoungSender")

        # 2 invitations (limit is 3)
        target1, _ = await _make_member(test_session, group, "Target1")
        target2, _ = await _make_member(test_session, group, "Target2")
        for t in [target1, target2]:
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status="pending",
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.YOUNG)
        assert result["allowed"] is True
        assert result["sent_today"] == 2
        assert result["daily_limit"] == 3
        assert result["remaining"] == 1

    @pytest.mark.asyncio
    async def test_young_at_limit_denied(self, test_session):
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "YoungFull")

        for i in range(3):
            t, _ = await _make_member(test_session, group, f"T{i}")
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status="pending",
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.YOUNG)
        assert result["allowed"] is False
        assert result["remaining"] == 0

    @pytest.mark.asyncio
    async def test_preteen_limit_is_10(self, test_session):
        result = await check_invitation_rate(test_session, uuid4(), AgeTier.PRETEEN)
        assert result["daily_limit"] == 10
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_teen_limit_is_10(self, test_session):
        result = await check_invitation_rate(test_session, uuid4(), AgeTier.TEEN)
        assert result["daily_limit"] == 10
        assert result["allowed"] is True

    def test_invitation_limits_constant(self):
        """Verify the per-tier limits match spec."""
        assert INVITATION_LIMITS[AgeTier.YOUNG] == 3
        assert INVITATION_LIMITS[AgeTier.PRETEEN] == 10
        assert INVITATION_LIMITS[AgeTier.TEEN] == 10


# ===========================================================================
# 8. Content Manipulation Tests
# ===========================================================================


class TestContentManipulation:
    """Tests for check_content_manipulation and normalization helpers."""

    def test_leetspeak_normalization(self):
        # 1 -> i, 0 -> o, 3 -> e in the mapping
        assert normalize_leetspeak("h3ll0 w0r1d") == "hello worid"
        assert normalize_leetspeak("h3ll0") == "hello"

    def test_homoglyph_normalization(self):
        # Cyrillic а, е, о → Latin a, e, o
        assert normalize_homoglyphs("\u0430\u0435\u043e") == "aeo"

    def test_no_manipulation_clean_text(self):
        result = check_content_manipulation("hello world", blocklist=["bad"])
        assert result["manipulated"] is False
        assert result["homoglyph_count"] == 0
        assert result["leetspeak_count"] == 0

    def test_leetspeak_bypass_detected(self):
        """Leetspeak used to bypass blocklist should be detected."""
        result = check_content_manipulation("h4t3", blocklist=["hate"])
        assert result["manipulated"] is True
        assert "hate" in result["matched_terms"]
        assert result["leetspeak_count"] > 0

    def test_homoglyph_bypass_detected(self):
        """Cyrillic homoglyphs used to bypass blocklist should be detected."""
        # "\u0430ss" looks like "ass" but uses Cyrillic а
        result = check_content_manipulation("\u0430ss", blocklist=["ass"])
        assert result["manipulated"] is True
        assert result["homoglyph_count"] == 1

    def test_no_blocklist_no_match(self):
        """Without a blocklist, manipulated is False even with homoglyphs."""
        result = check_content_manipulation("\u0430\u0435", blocklist=None)
        assert result["manipulated"] is False
        assert result["homoglyph_count"] == 2

    def test_blocklist_no_manipulation_no_flag(self):
        """Blocklist term present but written normally = no manipulation flag."""
        result = check_content_manipulation("this is bad content", blocklist=["bad"])
        assert result["manipulated"] is False
        assert result["matched_terms"] == ["bad"]

    def test_normalized_text_returned(self):
        result = check_content_manipulation("h3llo", blocklist=[])
        assert result["normalized_text"] == "hello"


# ===========================================================================
# 9. Record Abuse Signal (DB persistence)
# ===========================================================================


class TestRecordAbuseSignal:
    """Tests for record_abuse_signal."""

    @pytest.mark.asyncio
    async def test_record_signal(self, test_session):
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "Flagged")

        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type="age_misrepresentation",
            severity="high",
            details={"vocab_complexity": 7.5},
        )
        assert signal.id is not None
        assert signal.signal_type == "age_misrepresentation"
        assert signal.severity == "high"
        assert signal.resolved is False

    @pytest.mark.asyncio
    async def test_signal_persisted_in_db(self, test_session):
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "Persisted")

        await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type="account_farming",
            severity="critical",
        )
        await test_session.commit()

        result = await test_session.execute(
            select(AbuseSignal).where(AbuseSignal.member_id == member.id)
        )
        signals = result.scalars().all()
        assert len(signals) == 1
        assert signals[0].signal_type == "account_farming"


# ===========================================================================
# 10. AbuseType enum
# ===========================================================================


class TestAbuseTypeEnum:
    """Tests for the AbuseType StrEnum."""

    def test_values(self):
        assert AbuseType.AGE_MISREPRESENTATION == "age_misrepresentation"
        assert AbuseType.ACCOUNT_FARMING == "account_farming"
        assert AbuseType.COORDINATED_HARASSMENT == "coordinated_harassment"
        assert AbuseType.REPORT_ABUSE == "report_abuse"
        assert AbuseType.INVITATION_RATE == "invitation_rate"
        assert AbuseType.CONTENT_MANIPULATION == "content_manipulation"
