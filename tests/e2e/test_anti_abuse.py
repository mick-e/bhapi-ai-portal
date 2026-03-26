"""End-to-end tests for anti-abuse detection pipeline.

Tests the full flow: data setup -> detection -> signal recording.
Target: 20+ E2E tests.
"""

from datetime import datetime, timezone
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
    record_abuse_signal,
)
from src.moderation.models import ContentReport
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_member(session, group, name="Child") -> tuple[GroupMember, User]:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"e2e-{uuid4().hex[:8]}@example.com",
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
# E2E: Age Misrepresentation -> Record Signal
# ===========================================================================


class TestAgeMisrepresentationE2E:

    @pytest.mark.asyncio
    async def test_detect_and_record_young_vocab_misrepresentation(self, test_session):
        """Full flow: detect vocabulary mismatch for young tier, record abuse signal."""
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "FakeYoung")

        result = detect_age_misrepresentation(
            text="The epistemological considerations underlying these philosophical arguments",
            post_times=[datetime(2026, 3, 21, 14, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is True

        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type=AbuseType.AGE_MISREPRESENTATION,
            severity=result["severity"],
            details=result,
        )
        await test_session.commit()

        # Verify persisted
        q = await test_session.execute(
            select(AbuseSignal).where(AbuseSignal.id == signal.id)
        )
        persisted = q.scalar_one()
        assert persisted.signal_type == "age_misrepresentation"
        assert persisted.details["flagged"] is True

    @pytest.mark.asyncio
    async def test_detect_and_record_curfew_violation(self, test_session):
        """Full flow: detect curfew violation, record signal."""
        group, _ = await make_test_group(test_session)
        member, _ = await _make_member(test_session, group, "NightOwl")

        late_times = [
            datetime(2026, 3, 21, 23, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 22, 2, 0, tzinfo=timezone.utc),
        ]
        result = detect_age_misrepresentation(
            text="hi",
            post_times=late_times,
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["curfew_violations"] == 2

        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type=AbuseType.AGE_MISREPRESENTATION,
            severity=result["severity"],
        )
        await test_session.commit()
        assert signal.severity in ("medium", "high")

    @pytest.mark.asyncio
    async def test_clean_young_user_no_signal(self, test_session):
        """Legitimate young user should not trigger any signal."""
        result = detect_age_misrepresentation(
            text="I like cats",
            post_times=[datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc)],
            claimed_tier=AgeTier.YOUNG,
        )
        assert result["flagged"] is False
        assert result["severity"] == "low"


# ===========================================================================
# E2E: Account Farming -> Record Signal
# ===========================================================================


class TestAccountFarmingE2E:

    @pytest.mark.asyncio
    async def test_farming_detection_full_flow(self, test_session):
        """Create multiple accounts on same device, detect farming, record signal."""
        group, _ = await make_test_group(test_session)
        device_id = "e2e-farm-device"

        members = []
        for i in range(5):
            member, _ = await _make_member(test_session, group, f"Farm{i}")
            members.append(member)
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
        assert result["flagged"] is True
        assert result["account_count"] == 5

        signal = await record_abuse_signal(
            test_session,
            member_id=members[0].id,
            signal_type=AbuseType.ACCOUNT_FARMING,
            severity=result["severity"],
            details=result,
        )
        await test_session.commit()

        q = await test_session.execute(
            select(AbuseSignal).where(AbuseSignal.id == signal.id)
        )
        assert q.scalar_one().signal_type == "account_farming"

    @pytest.mark.asyncio
    async def test_different_devices_no_farming(self, test_session):
        """Different devices for different accounts should not flag."""
        group, _ = await make_test_group(test_session)

        for i in range(5):
            member, _ = await _make_member(test_session, group, f"Legit{i}")
            test_session.add(DeviceSession(
                id=uuid4(),
                member_id=member.id,
                group_id=group.id,
                device_id=f"unique-device-{i}",
                device_type="ios",
                started_at=datetime.now(timezone.utc),
            ))
        await test_session.flush()

        for i in range(5):
            result = await detect_account_farming(test_session, f"unique-device-{i}")
            assert result["flagged"] is False


# ===========================================================================
# E2E: Coordinated Harassment -> Record Signal
# ===========================================================================


class TestCoordinatedHarassmentE2E:

    @pytest.mark.asyncio
    async def test_harassment_detection_full_flow(self, test_session):
        """Multiple reporters targeting same user, detect and record."""
        group, _ = await make_test_group(test_session)
        target_id = uuid4()

        for i in range(5):
            _, user = await _make_member(test_session, group, f"Harasser{i}")
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
        assert result["reporter_count"] == 5

        # Record for first reporter
        _, first_reporter = await _make_member(test_session, group, "FirstReporter")
        signal = await record_abuse_signal(
            test_session,
            member_id=(await _make_member(test_session, group, "TargetMember"))[0].id,
            signal_type=AbuseType.COORDINATED_HARASSMENT,
            severity=result["severity"],
            details={"target_id": str(target_id), "reporter_count": result["reporter_count"]},
        )
        await test_session.commit()
        assert signal.signal_type == "coordinated_harassment"

    @pytest.mark.asyncio
    async def test_no_harassment_few_reporters(self, test_session):
        """Two reporters should not trigger harassment detection."""
        group, _ = await make_test_group(test_session)
        target_id = uuid4()

        for i in range(2):
            _, user = await _make_member(test_session, group, f"R{i}")
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


# ===========================================================================
# E2E: Report Abuse -> Record Signal
# ===========================================================================


class TestReportAbuseE2E:

    @pytest.mark.asyncio
    async def test_serial_false_reporter_full_flow(self, test_session):
        """User with 90% dismissed reports should be flagged."""
        group, _ = await make_test_group(test_session)
        _, abuser = await _make_member(test_session, group, "FalseReporter")

        for i in range(9):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=abuser.id,
                target_type="post",
                target_id=uuid4(),
                reason="spam",
                status="dismissed",
            ))
        test_session.add(ContentReport(
            id=uuid4(),
            reporter_id=abuser.id,
            target_type="post",
            target_id=uuid4(),
            reason="spam",
            status="action_taken",
        ))
        await test_session.flush()

        result = await detect_report_abuse(test_session, abuser.id)
        assert result["flagged"] is True
        assert result["dismiss_rate"] == pytest.approx(0.9)

        member, _ = await _make_member(test_session, group, "AbuserMember")
        signal = await record_abuse_signal(
            test_session,
            member_id=member.id,
            signal_type=AbuseType.REPORT_ABUSE,
            severity=result["severity"],
        )
        await test_session.commit()
        assert signal.severity == "medium"  # 90% < 95% threshold for "high"

    @pytest.mark.asyncio
    async def test_honest_reporter_no_flag(self, test_session):
        """User with mostly confirmed reports should not be flagged."""
        group, _ = await make_test_group(test_session)
        _, honest = await _make_member(test_session, group, "HonestReporter")

        for i in range(8):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=honest.id,
                target_type="post",
                target_id=uuid4(),
                reason="bullying",
                status="action_taken",
            ))
        for i in range(2):
            test_session.add(ContentReport(
                id=uuid4(),
                reporter_id=honest.id,
                target_type="post",
                target_id=uuid4(),
                reason="bullying",
                status="dismissed",
            ))
        await test_session.flush()

        result = await detect_report_abuse(test_session, honest.id)
        assert result["flagged"] is False
        assert result["dismiss_rate"] == pytest.approx(0.2)


# ===========================================================================
# E2E: Invitation Rate Limiting
# ===========================================================================


class TestInvitationRateE2E:

    @pytest.mark.asyncio
    async def test_young_hits_limit(self, test_session):
        """Young user hitting 3/day limit should be denied."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "YoungSpammer")

        for i in range(3):
            t, _ = await _make_member(test_session, group, f"Target{i}")
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status="pending",
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.YOUNG)
        assert result["allowed"] is False
        assert result["sent_today"] == 3
        assert result["remaining"] == 0

    @pytest.mark.asyncio
    async def test_preteen_under_limit(self, test_session):
        """Preteen with 5 invitations should still be allowed (limit 10)."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "PreteenUser")

        for i in range(5):
            t, _ = await _make_member(test_session, group, f"PT{i}")
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status="pending",
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.PRETEEN)
        assert result["allowed"] is True
        assert result["remaining"] == 5

    @pytest.mark.asyncio
    async def test_teen_at_limit(self, test_session):
        """Teen hitting 10/day limit should be denied."""
        group, _ = await make_test_group(test_session)
        _, user = await _make_member(test_session, group, "TeenSpammer")

        for i in range(10):
            t, _ = await _make_member(test_session, group, f"TT{i}")
            test_session.add(Contact(
                id=uuid4(),
                requester_id=user.id,
                target_id=t.user_id,
                status="pending",
            ))
        await test_session.flush()

        result = await check_invitation_rate(test_session, user.id, AgeTier.TEEN)
        assert result["allowed"] is False
        assert result["remaining"] == 0


# ===========================================================================
# E2E: Content Manipulation
# ===========================================================================


class TestContentManipulationE2E:

    def test_leetspeak_circumvention_detected(self):
        """Full flow: user tries to bypass filter with leetspeak."""
        result = check_content_manipulation(
            "y0u 4r3 $tup1d",
            blocklist=["stupid"],
        )
        assert result["manipulated"] is True
        assert "stupid" in result["matched_terms"]

    def test_homoglyph_circumvention_detected(self):
        """Full flow: user uses Cyrillic to bypass filter."""
        # "\u0445\u0430te" = хаte (Cyrillic х and а look like x and a)
        result = check_content_manipulation(
            "\u0445\u0430te",
            blocklist=["xate", "hate"],
        )
        assert result["homoglyph_count"] == 2

    def test_mixed_manipulation(self):
        """Combination of leetspeak + homoglyphs."""
        # "\u0430$$h0l3" — Cyrillic а + leetspeak
        result = check_content_manipulation(
            "\u0430$$h0l3",
            blocklist=["asshole"],
        )
        assert result["manipulated"] is True
        assert "asshole" in result["matched_terms"]

    def test_clean_text_passes(self):
        """Normal text should not be flagged."""
        result = check_content_manipulation(
            "I love my cat and my dog",
            blocklist=["bad", "hate", "stupid"],
        )
        assert result["manipulated"] is False
        assert result["matched_terms"] == []
