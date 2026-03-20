"""E2E tests for anomaly detection and peer comparison endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.analytics.service import detect_anomalies, get_peer_comparison
from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_anomalies_endpoint_empty_group(test_session):
    """Anomaly endpoint returns empty anomalies for group with no activity."""
    group, _ = await make_test_group(test_session, name="Empty", group_type="family")
    await test_session.flush()

    result = await detect_anomalies(test_session, group.id)
    assert result["group_id"] == str(group.id)
    assert result["threshold_sd"] == 2.0
    assert isinstance(result["anomalies"], list)
    assert len(result["anomalies"]) == 0


@pytest.mark.asyncio
async def test_anomalies_endpoint_returns_flagged_members(test_session):
    """Anomaly endpoint returns flagged members with correct structure."""
    group, _ = await make_test_group(test_session, name="Anomaly", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="AnomalyKid",
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

    # Spike: 100 events/day for last 7 days (huge contrast vs baseline)
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
    assert len(result["anomalies"]) >= 1

    anomaly = result["anomalies"][0]
    # Validate response structure
    assert "member_id" in anomaly
    assert "member_name" in anomaly
    assert "recent_daily_avg" in anomaly
    assert "baseline_daily_avg" in anomaly
    assert "standard_deviations" in anomaly
    assert "direction" in anomaly
    assert "severity" in anomaly
    assert anomaly["member_name"] == "AnomalyKid"
    assert anomaly["direction"] == "above"
    assert anomaly["severity"] in ("warning", "critical")


@pytest.mark.asyncio
async def test_anomalies_endpoint_respects_threshold(test_session):
    """Different thresholds should produce different results."""
    group, _ = await make_test_group(test_session, name="Threshold", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Moderate variance baseline
    for day in range(8, 25):
        count = 3 if day % 2 == 0 else 5
        for i in range(count):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"b{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)

    # Recent moderate increase: 10 events/day
    for day in range(7):
        for i in range(10):
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

    result_low = await detect_anomalies(test_session, group.id, threshold_sd=1.0)
    result_high = await detect_anomalies(test_session, group.id, threshold_sd=5.0)

    assert result_low["threshold_sd"] == 1.0
    assert result_high["threshold_sd"] == 5.0
    # Lower threshold should find at least as many anomalies
    assert len(result_low["anomalies"]) >= len(result_high["anomalies"])


@pytest.mark.asyncio
async def test_peer_comparison_endpoint_empty(test_session):
    """Peer comparison for empty group returns valid structure."""
    group, _ = await make_test_group(test_session, name="Empty", group_type="family")
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert result["group_id"] == str(group.id)
    assert result["period_days"] == 30
    assert result["members"] == []


@pytest.mark.asyncio
async def test_peer_comparison_endpoint_with_data(test_session):
    """Peer comparison returns correct percentiles for multiple members."""
    group, _ = await make_test_group(test_session, name="School", group_type="school")

    members = []
    for name in ["Alice", "Bob", "Charlie", "Diana", "Eve"]:
        m = GroupMember(
            id=uuid4(), group_id=group.id, user_id=None,
            role="member", display_name=name,
        )
        test_session.add(m)
        members.append(m)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    # Alice: 5, Bob: 10, Charlie: 15, Diana: 20, Eve: 25
    counts = [5, 10, 15, 20, 25]
    for member, count in zip(members, counts):
        for i in range(count):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="gemini", session_id=f"{member.display_name}_{i}",
                event_type="prompt",
                timestamp=now - timedelta(hours=i % 24, minutes=i),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result = await get_peer_comparison(test_session, group.id, days=30)
    assert len(result["members"]) == 5

    # Validate structure
    for m in result["members"]:
        assert "member_id" in m
        assert "member_name" in m
        assert "event_count" in m
        assert "percentile" in m
        assert "usage_level" in m
        assert m["usage_level"] in ("low", "moderate", "high", "very_high")

    # Eve (most events) should be first (sorted by percentile desc)
    assert result["members"][0]["member_name"] == "Eve"
    assert result["members"][0]["event_count"] == 25

    # Alice (fewest events) should be last
    assert result["members"][-1]["member_name"] == "Alice"
    assert result["members"][-1]["event_count"] == 5


@pytest.mark.asyncio
async def test_peer_comparison_custom_days(test_session):
    """Peer comparison respects the days parameter."""
    group, _ = await make_test_group(test_session, name="Days", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Events spread across different time ranges
    # 5 events in last 7 days
    for i in range(5):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"recent{i}",
            event_type="prompt",
            timestamp=now - timedelta(days=3, hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)

    # 10 more events between 8-20 days ago
    for i in range(10):
        event = CaptureEvent(
            id=uuid4(), group_id=group.id, member_id=member.id,
            platform="chatgpt", session_id=f"older{i}",
            event_type="prompt",
            timestamp=now - timedelta(days=15, hours=i),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    await test_session.flush()

    result_7 = await get_peer_comparison(test_session, group.id, days=7)
    result_30 = await get_peer_comparison(test_session, group.id, days=30)

    assert result_7["period_days"] == 7
    assert result_30["period_days"] == 30

    # 30-day window should capture more events
    assert result_30["members"][0]["event_count"] >= result_7["members"][0]["event_count"]


@pytest.mark.asyncio
async def test_anomalies_cross_group_isolation(test_session):
    """Anomalies from one group should not appear in another."""
    group1, _ = await make_test_group(test_session, name="Group1", group_type="family")
    group2, _ = await make_test_group(test_session, name="Group2", group_type="family")

    member1 = GroupMember(
        id=uuid4(), group_id=group1.id, user_id=None,
        role="member", display_name="Child1",
    )
    member2 = GroupMember(
        id=uuid4(), group_id=group2.id, user_id=None,
        role="member", display_name="Child2",
    )
    test_session.add(member1)
    test_session.add(member2)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Create anomalous data only for group1
    # Baseline: 1 event/day for days 7-29 (23 days of low, consistent usage)
    for day in range(7, 30):
        event = CaptureEvent(
            id=uuid4(), group_id=group1.id, member_id=member1.id,
            platform="chatgpt", session_id=f"g1b{day}e0",
            event_type="prompt",
            timestamp=now - timedelta(days=day, hours=1),
            risk_processed=False,
            source_channel="extension",
        )
        test_session.add(event)
    # Spike: 100 events/day for last 7 days
    for day in range(7):
        for i in range(100):
            event = CaptureEvent(
                id=uuid4(), group_id=group1.id, member_id=member1.id,
                platform="chatgpt", session_id=f"g1r{day}e{i}",
                event_type="prompt",
                timestamp=now - timedelta(days=day, hours=i % 12),
                risk_processed=False,
                source_channel="extension",
            )
            test_session.add(event)
    await test_session.flush()

    result1 = await detect_anomalies(test_session, group1.id, threshold_sd=1.5)
    result2 = await detect_anomalies(test_session, group2.id, threshold_sd=1.5)

    assert len(result1["anomalies"]) >= 1
    assert len(result2["anomalies"]) == 0


@pytest.mark.asyncio
async def test_peer_comparison_cross_group_isolation(test_session):
    """Peer comparison for one group should not include other groups' members."""
    group1, _ = await make_test_group(test_session, name="G1", group_type="family")
    group2, _ = await make_test_group(test_session, name="G2", group_type="family")

    m1 = GroupMember(
        id=uuid4(), group_id=group1.id, user_id=None,
        role="member", display_name="G1Child",
    )
    m2 = GroupMember(
        id=uuid4(), group_id=group2.id, user_id=None,
        role="member", display_name="G2Child",
    )
    test_session.add(m1)
    test_session.add(m2)
    await test_session.flush()

    result1 = await get_peer_comparison(test_session, group1.id, days=30)
    result2 = await get_peer_comparison(test_session, group2.id, days=30)

    names1 = [m["member_name"] for m in result1["members"]]
    names2 = [m["member_name"] for m in result2["members"]]

    assert "G1Child" in names1
    assert "G2Child" not in names1
    assert "G2Child" in names2
    assert "G1Child" not in names2
