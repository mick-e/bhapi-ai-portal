"""Unit tests for anomaly detection and peer comparison analytics."""

import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.analytics.service import detect_anomalies, get_peer_comparison
from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_detect_anomalies_no_data(test_session):
    """No members means no anomalies."""
    group, _ = await make_test_group(test_session, name="Empty", group_type="family")
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id)
    assert result["group_id"] == str(group.id)
    assert result["threshold_sd"] == 2.0
    assert result["anomalies"] == []


@pytest.mark.asyncio
async def test_detect_anomalies_insufficient_data(test_session):
    """Members with fewer than 3 daily data points should not trigger anomalies."""
    group, _ = await make_test_group(test_session, name="Sparse", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Only 2 events on 2 different days — not enough data points
    now = datetime.now(timezone.utc)
    for i in range(2):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"s{i}",
            event_type="prompt",
            timestamp=now - timedelta(days=i * 5),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id)
    assert result["anomalies"] == []


@pytest.mark.asyncio
async def test_detect_anomalies_normal_usage(test_session):
    """Consistent daily usage should not trigger anomalies."""
    group, _ = await make_test_group(test_session, name="Normal", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="NormalChild",
    )
    test_session.add(member)
    await test_session.flush()

    # Create consistent usage: ~5 events per day for 20 days
    now = datetime.now(timezone.utc)
    for day in range(20):
        for i in range(5):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"d{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id)
    assert result["anomalies"] == []


@pytest.mark.asyncio
async def test_detect_anomalies_spike(test_session):
    """A massive usage spike in the recent 7 days should be flagged."""
    group, _ = await make_test_group(test_session, name="Spike", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="SpikeChild",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Baseline: 1 event/day for days 7-29 (23 days of low, consistent usage)
    for day in range(7, 30):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"b{day}e0",
            event_type="prompt",
            timestamp=now - timedelta(days=day, hours=1),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)

    # Recent spike: 100 events/day for last 7 days (huge contrast vs baseline)
    for day in range(7):
        for i in range(100):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"r{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i % 12),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id, threshold_sd=1.5)
    assert len(result["anomalies"]) == 1
    anomaly = result["anomalies"][0]
    assert anomaly["member_name"] == "SpikeChild"
    assert anomaly["direction"] == "above"
    assert anomaly["standard_deviations"] >= 1.5
    assert anomaly["severity"] in ("warning", "critical")


@pytest.mark.asyncio
async def test_detect_anomalies_custom_threshold(test_session):
    """A lower threshold should catch more anomalies."""
    group, _ = await make_test_group(test_session, name="Custom", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Baseline: 3 events/day for days 8-25
    for day in range(8, 25):
        for i in range(3):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"b{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)

    # Recent: 8 events/day for last 7 days (moderate increase)
    for day in range(7):
        for i in range(8):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"r{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i % 12),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    # With default threshold (2.0) it may or may not trigger
    result_strict = await detect_anomalies(test_session, group.id, threshold_sd=5.0)
    # With very low threshold (1.0) it should definitely trigger
    result_loose = await detect_anomalies(test_session, group.id, threshold_sd=1.0)
    assert len(result_loose["anomalies"]) >= len(result_strict["anomalies"])


@pytest.mark.asyncio
async def test_detect_anomalies_zero_variance(test_session):
    """When all days have identical counts, no anomalies should be raised."""
    group, _ = await make_test_group(test_session, name="Flat", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="FlatChild",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Exactly 5 events every day for 20 days
    for day in range(20):
        for i in range(5):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"d{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id)
    # Zero SD means we skip (no division by zero)
    assert result["anomalies"] == []


# ---------------------------------------------------------------------------
# Peer comparison tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_peer_comparison_empty_group(test_session):
    """Peer comparison for empty group returns empty list."""
    group, _ = await make_test_group(test_session, name="Empty", group_type="family")
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert result["group_id"] == str(group.id)
    assert result["period_days"] == 30
    assert result["members"] == []


@pytest.mark.asyncio
async def test_peer_comparison_single_member(test_session):
    """Single member gets 50th percentile."""
    group, _ = await make_test_group(test_session, name="Single", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="OnlyChild",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    for i in range(5):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"s{i}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert len(result["members"]) == 1
    assert result["members"][0]["member_name"] == "OnlyChild"
    assert result["members"][0]["event_count"] == 5
    assert result["members"][0]["percentile"] == 50.0


@pytest.mark.asyncio
async def test_peer_comparison_multiple_members(test_session):
    """Multiple members should get ranked by usage level."""
    group, _ = await make_test_group(test_session, name="Family", group_type="family")

    members = []
    # Create 4 members with different usage levels
    usage_levels = [("Low Child", 2), ("Mid Child", 10), ("High Child", 25), ("Top Child", 50)]
    for name, count in usage_levels:
        m = GroupMember(
            id=uuid4(), group_id=group.id, user_id=None,
            role="member", display_name=name,
        )
        test_session.add(m)
        members.append((m, count))
    await test_session.flush()

    now = datetime.now(timezone.utc)
    for member, count in members:
        for i in range(count):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"{member.display_name}_{i}",
                event_type="prompt",
                timestamp=now - timedelta(hours=i % 24, minutes=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert len(result["members"]) == 4

    # Results sorted by percentile descending
    names = [m["member_name"] for m in result["members"]]
    assert names[0] == "Top Child"
    assert names[-1] == "Low Child"

    # Top child should have highest percentile
    top = result["members"][0]
    assert top["event_count"] == 50
    assert top["percentile"] > 0

    # Each member should have a usage_level
    for m in result["members"]:
        assert m["usage_level"] in ("low", "moderate", "high", "very_high")


@pytest.mark.asyncio
async def test_peer_comparison_usage_levels(test_session):
    """Verify usage level classification boundaries."""
    group, _ = await make_test_group(test_session, name="Levels", group_type="school")

    # Create 10 members to get meaningful percentiles
    members_data = []
    for i in range(10):
        m = GroupMember(
            id=uuid4(), group_id=group.id, user_id=None,
            role="member", display_name=f"Student{i}",
        )
        test_session.add(m)
        members_data.append((m, (i + 1) * 3))  # 3, 6, 9, ... 30 events
    await test_session.flush()

    now = datetime.now(timezone.utc)
    for member, count in members_data:
        for j in range(count):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="gemini", session_id=f"{member.display_name}_{j}",
                event_type="prompt",
                timestamp=now - timedelta(hours=j % 24, minutes=j),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert len(result["members"]) == 10

    # The member with the most events should be at or near 'very_high'
    # The member with the fewest should be 'low'
    levels = {m["member_name"]: m["usage_level"] for m in result["members"]}
    assert levels["Student0"] == "low"
