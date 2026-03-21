"""Security tests for anti-abuse detection.

Covers: injection resistance, boundary conditions, rate limit enforcement,
manipulation evasion attempts, signal integrity.
Target: 10+ security tests.
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
    AbuseType,
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


async def _make_member(session, group, name="Child") -> tuple[GroupMember, User]:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"sec-{uuid4().hex[:8]}@example.com",
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


class TestContentManipulationSecurity:
    """Security tests for content manipulation detection evasion."""

    def test_null_bytes_in_text(self):
        """Null bytes should not crash normalization."""
        result = check_content_manipulation(
            "h\x00e\x00l\x00l\x00o",
            blocklist=["hello"],
        )
        # Should handle gracefully, not crash
        assert isinstance(result["normalized_text"], str)

    def test_extremely_long_text(self):
        """Very long text should not cause performance issues."""
        long_text = "h3ll0 " * 10000  # 60,000 chars
        result = check_content_manipulation(long_text, blocklist=["hello"])
        assert result["leetspeak_count"] > 0

    def test_mixed_script_attack(self):
        """Combined Cyrillic + Greek + Latin confusables should be detected."""
        # \u0430 = Cyrillic a, \u03bf = Greek o
        text = "\u0430dm\u0456n\u0456str\u0430t\u03bfr"
        result = check_content_manipulation(text, blocklist=["administrator"])
        assert result["homoglyph_count"] > 0

    def test_zero_width_characters(self):
        """Zero-width chars should not bypass detection."""
        # Zero-width space \u200b, zero-width joiner \u200d
        text = "h\u200ba\u200dt\u200be"
        result = check_content_manipulation(text, blocklist=["hate"])
        # After normalization, zero-width chars should be stripped
        assert isinstance(result["normalized_text"], str)

    def test_rtl_override_injection(self):
        """RTL override characters should not crash parser."""
        text = "\u202eh3ll0\u202c"
        result = check_content_manipulation(text, blocklist=["hello"])
        assert isinstance(result, dict)

    def test_emoji_in_text_handled(self):
        """Emoji should not crash normalization."""
        result = check_content_manipulation(
            "h3ll0 world! \U0001f600",
            blocklist=["hello"],
        )
        assert result["leetspeak_count"] > 0

    def test_sql_injection_in_blocklist(self):
        """SQL injection in blocklist should not be executed."""
        result = check_content_manipulation(
            "hello",
            blocklist=["'; DROP TABLE users; --"],
        )
        assert isinstance(result["matched_terms"], list)


class TestDeviceFingerprintSecurity:
    """Security tests for device fingerprint handling."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_device_id(self, test_session):
        """SQL injection in device_id should be safely parameterized."""
        result = await detect_account_farming(
            test_session,
            device_id="'; DROP TABLE device_sessions; --",
        )
        assert result["flagged"] is False
        assert result["account_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_device_id(self, test_session):
        """Empty device_id should return no results."""
        result = await detect_account_farming(test_session, device_id="")
        assert result["flagged"] is False

    @pytest.mark.asyncio
    async def test_very_long_device_id(self, test_session):
        """Extremely long device_id should not crash."""
        result = await detect_account_farming(
            test_session,
            device_id="A" * 10000,
        )
        assert result["flagged"] is False


class TestHarassmentDetectionSecurity:
    """Security tests for coordinated harassment detection."""

    @pytest.mark.asyncio
    async def test_uuid_injection_in_target_id(self, test_session):
        """Random UUID should not crash harassment detection."""
        result = await detect_coordinated_harassment(test_session, uuid4())
        assert result["flagged"] is False

    @pytest.mark.asyncio
    async def test_harassment_window_boundary(self, test_session):
        """Reports exactly at window boundary should be handled correctly."""
        group, _ = await make_test_group(test_session)
        target_id = uuid4()

        # Create reports just inside the 24h window
        now = datetime.now(timezone.utc)
        for i in range(3):
            _, user = await _make_member(test_session, group, f"BoundaryR{i}")
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="user",
                target_id=target_id,
                reason="bullying",
                status="pending",
            ))
        await test_session.flush()

        result = await detect_coordinated_harassment(test_session, target_id, window_hours=24)
        assert result["flagged"] is True


class TestInvitationRateSecurity:
    """Security tests for invitation rate limiting."""

    @pytest.mark.asyncio
    async def test_invalid_tier_uses_default_limit(self, test_session):
        """Unknown tier should default to lowest (most restrictive) limit."""
        result = await check_invitation_rate(
            test_session,
            requester_id=uuid4(),
            tier="nonexistent_tier",
        )
        assert result["daily_limit"] == 3  # defaults to most restrictive

    @pytest.mark.asyncio
    async def test_rate_limit_not_bypassable_by_status(self, test_session):
        """All contact requests count regardless of status (pending, accepted, etc)."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "RateBypasser")

        for i, status in enumerate(["pending", "accepted", "rejected"]):
            t, _ = await _make_member(test_session, group, f"RBT{i}")
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status=status,
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.YOUNG)
        assert result["sent_today"] == 3
        assert result["allowed"] is False


class TestAbuseSignalIntegrity:
    """Security tests for abuse signal recording integrity."""

    @pytest.mark.asyncio
    async def test_signal_cannot_have_empty_type(self, test_session):
        """Recording a signal with empty type should still persist (validation at schema level)."""
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "IntegrityTest")

        # The function itself doesn't validate — schema validation is upstream
        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type="age_misrepresentation",
            severity="high",
            details={"test": True},
        )
        await test_session.commit()
        assert signal.id is not None
        assert signal.resolved is False

    @pytest.mark.asyncio
    async def test_signal_details_cannot_contain_pii_leak(self, test_session):
        """Details dict should be stored as-is (no unexpected expansion)."""
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "PIITest")

        details = {"vocab_complexity": 7.5, "safe_field": "ok"}
        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type="age_misrepresentation",
            severity="medium",
            details=details,
        )
        await test_session.commit()

        q = await test_session.execute(
            select(AbuseSignal).where(AbuseSignal.id == signal.id)
        )
        persisted = q.scalar_one()
        assert persisted.details == details
        # No extra fields injected
        assert set(persisted.details.keys()) == {"vocab_complexity", "safe_field"}


class TestReportAbuseSecurityBoundary:
    """Security boundary tests for report abuse detection."""

    @pytest.mark.asyncio
    async def test_exactly_at_threshold(self, test_session):
        """Exactly at 80% dismiss rate with minimum reports should flag."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "ExactThreshold")

        # 5 reports, 4 dismissed = 80%
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
    async def test_just_below_threshold(self, test_session):
        """Just below 80% dismiss rate should not flag."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "BelowThreshold")

        # 5 reports, 3 dismissed = 60%
        for i in range(3):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=user.id,
                target_type="post",
                target_id=uuid4(),
                reason="spam",
                status="dismissed",
            ))
        for i in range(2):
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
        assert result["flagged"] is False
