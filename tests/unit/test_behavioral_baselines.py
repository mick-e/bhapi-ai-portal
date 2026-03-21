"""Unit tests for behavioral baselines — per-child norms, deviation alerting."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.auth.models import User
from src.device_agent.models import DeviceSession
from src.groups.models import GroupMember
from src.intelligence.models import BehavioralBaseline
from src.messaging.models import Conversation, Message
from src.social.behavioral import (
    _mean_std,
    _pad_daily,
    compute_baseline,
    detect_deviation,
    get_baseline_summary,
    update_baselines_batch,
)
from src.social.models import SocialPost
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_member(session, group, name="Child") -> GroupMember:
    """Create a User + GroupMember linked together.

    SocialPost.author_id and Message.sender_id reference users.id,
    while DeviceSession.member_id references group_members.id.
    We need both to satisfy FK constraints.
    """
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"child-{uuid4().hex[:8]}@example.com",
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
    return member


async def _make_posts_on_days(session, user_id, posts_per_day: list[int]):
    """Create posts with specific counts per day.

    posts_per_day[0] = today, posts_per_day[1] = yesterday, etc.
    Uses user_id (users.id) as author_id.
    """
    now = datetime.now(timezone.utc)
    for day_idx, count in enumerate(posts_per_day):
        for i in range(count):
            post = SocialPost(
                id=uuid4(),
                author_id=user_id,
                content=f"Post day-{day_idx} #{i}",
                post_type="text",
                moderation_status="approved",
            )
            session.add(post)
    await session.flush()

    # Update timestamps
    result = await session.execute(
        select(SocialPost).where(SocialPost.author_id == user_id)
    )
    posts = list(result.scalars().all())
    idx = 0
    for day_idx, count in enumerate(posts_per_day):
        for _ in range(count):
            posts[idx].created_at = now - timedelta(days=day_idx, hours=1)
            idx += 1
    await session.flush()


async def _make_messages(session, user_id, count, days_back=14):
    """Create messages spread over days_back days. Uses user_id."""
    now = datetime.now(timezone.utc)
    conv = Conversation(
        id=uuid4(), type="direct", created_by=user_id,
    )
    session.add(conv)
    await session.flush()

    for i in range(count):
        msg = Message(
            id=uuid4(),
            conversation_id=conv.id,
            sender_id=user_id,
            content=f"Message {i}",
            message_type="text",
            moderation_status="approved",
        )
        session.add(msg)
    await session.flush()

    result = await session.execute(
        select(Message).where(Message.sender_id == user_id)
    )
    msgs = list(result.scalars().all())
    for i, msg in enumerate(msgs):
        day_offset = i % days_back
        msg.created_at = now - timedelta(days=day_offset, hours=2)
    await session.flush()


async def _make_sessions(
    session, member_id, group_id, sessions_data: list[tuple[int, int]],
):
    """Create device sessions. Uses member_id (group_members.id)."""
    now = datetime.now(timezone.utc)
    for days_back, duration_min in sessions_data:
        started = now - timedelta(days=days_back, hours=3)
        ended = started + timedelta(minutes=duration_min)
        ds = DeviceSession(
            id=uuid4(),
            member_id=member_id,
            group_id=group_id,
            device_id="test-device",
            device_type="ios",
            started_at=started,
            ended_at=ended,
        )
        session.add(ds)
    await session.flush()


async def _make_spike_posts(session, user_id, count):
    """Create posts for the current day (spike)."""
    for i in range(count):
        post = SocialPost(
            id=uuid4(), author_id=user_id,
            content=f"Spike post {i}", post_type="text",
            moderation_status="approved",
        )
        session.add(post)
    await session.flush()


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_pad_daily_already_full():
    """Pad does nothing when list already has enough entries."""
    result = _pad_daily([1, 2, 3], 3)
    assert result == [1.0, 2.0, 3.0]


def test_pad_daily_adds_zeros():
    """Pad appends zeros to reach window_days."""
    result = _pad_daily([5], 4)
    assert result == [5.0, 0.0, 0.0, 0.0]


def test_pad_daily_empty():
    """Pad with empty list returns all zeros."""
    result = _pad_daily([], 3)
    assert result == [0.0, 0.0, 0.0]


def test_mean_std_empty():
    """Empty list gives zero mean and std."""
    mean, std = _mean_std([])
    assert mean == 0.0
    assert std == 0.0


def test_mean_std_uniform():
    """Uniform values give std of 0."""
    mean, std = _mean_std([5.0, 5.0, 5.0])
    assert mean == 5.0
    assert std == 0.0


def test_mean_std_varied():
    """Verify mean and std calculation with known values."""
    # [2, 4, 4, 4, 5, 5, 7, 9] -> mean=5, std=2
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    mean, std = _mean_std(values)
    assert mean == 5.0
    assert abs(std - 2.0) < 0.01


# ---------------------------------------------------------------------------
# compute_baseline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_baseline_no_activity(test_session):
    """Compute baseline with no activity -- all zeros."""
    group, _ = await make_test_group(test_session, name="Empty", group_type="family")
    member = await _make_member(test_session, group)

    baseline = await compute_baseline(test_session, member.id, window_days=14)

    assert baseline.member_id == member.id
    assert baseline.window_days == 14
    assert baseline.sample_count == 0
    assert baseline.metrics["avg_posts_per_day"]["mean"] == 0.0
    assert baseline.metrics["avg_messages_per_day"]["mean"] == 0.0
    assert baseline.metrics["avg_session_duration"]["mean"] == 0.0
    assert baseline.metrics["active_hours"] == []
    assert baseline.metrics["content_sentiment_avg"] == 0.0


@pytest.mark.asyncio
async def test_compute_baseline_with_posts(test_session):
    """Compute baseline with post activity."""
    group, _ = await make_test_group(test_session, name="Posts", group_type="family")
    member = await _make_member(test_session, group)

    await _make_posts_on_days(
        test_session, member.user_id, [2, 3, 1, 0, 4, 2, 1] + [0] * 7,
    )

    baseline = await compute_baseline(test_session, member.id, window_days=14)

    assert baseline.metrics["avg_posts_per_day"]["mean"] > 0
    assert baseline.sample_count > 0


@pytest.mark.asyncio
async def test_compute_baseline_with_messages(test_session):
    """Compute baseline with message activity."""
    group, _ = await make_test_group(test_session, name="Msgs", group_type="family")
    member = await _make_member(test_session, group)

    await _make_messages(test_session, member.user_id, count=28, days_back=14)

    baseline = await compute_baseline(test_session, member.id, window_days=14)

    assert baseline.metrics["avg_messages_per_day"]["mean"] > 0


@pytest.mark.asyncio
async def test_compute_baseline_with_sessions(test_session):
    """Compute baseline with device session data."""
    group, _ = await make_test_group(test_session, name="Sessions", group_type="family")
    member = await _make_member(test_session, group)

    await _make_sessions(test_session, member.id, group.id, [
        (0, 30), (1, 45), (2, 60), (3, 20), (4, 50),
        (5, 40), (6, 35), (7, 55), (8, 25), (9, 30),
    ])

    baseline = await compute_baseline(test_session, member.id, window_days=14)

    assert baseline.metrics["avg_session_duration"]["mean"] > 0
    assert len(baseline.metrics["active_hours"]) > 0


@pytest.mark.asyncio
async def test_compute_baseline_combined_activity(test_session):
    """Baseline from 14 days of combined activity -- posts, messages, sessions."""
    group, _ = await make_test_group(test_session, name="Combined", group_type="family")
    member = await _make_member(test_session, group)

    await _make_posts_on_days(
        test_session, member.user_id, [2, 3, 1, 2, 4, 2, 1] + [0] * 7,
    )
    await _make_messages(test_session, member.user_id, count=42, days_back=14)
    await _make_sessions(test_session, member.id, group.id, [
        (0, 30), (1, 45), (2, 60), (3, 20), (4, 50),
    ])

    baseline = await compute_baseline(test_session, member.id, window_days=14)

    assert baseline.metrics["avg_posts_per_day"]["mean"] > 0
    assert baseline.metrics["avg_messages_per_day"]["mean"] > 0
    assert baseline.metrics["avg_session_duration"]["mean"] > 0
    assert baseline.sample_count > 0
    assert baseline.window_days == 14
    assert baseline.computed_at is not None


@pytest.mark.asyncio
async def test_compute_baseline_window_7_days(test_session):
    """Shorter window should work correctly."""
    group, _ = await make_test_group(test_session, name="Short", group_type="family")
    member = await _make_member(test_session, group)

    await _make_posts_on_days(test_session, member.user_id, [3, 3, 3, 3, 3, 3, 3])

    baseline = await compute_baseline(test_session, member.id, window_days=7)

    assert baseline.window_days == 7


# ---------------------------------------------------------------------------
# detect_deviation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_deviation_no_baseline(test_session):
    """No baseline means no deviations detected."""
    member_id = uuid4()
    result = await detect_deviation(test_session, member_id)
    assert result == []


@pytest.mark.asyncio
async def test_detect_deviation_normal(test_session):
    """Activity within normal range should not trigger deviation."""
    group, _ = await make_test_group(test_session, name="Normal", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 3.0, "std": 1.0},
            "avg_messages_per_day": {"mean": 10.0, "std": 3.0},
            "avg_session_duration": {"mean": 40.0, "std": 10.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=50,
    )
    test_session.add(baseline)
    await test_session.flush()

    # 3 posts today = exactly the mean
    await _make_spike_posts(test_session, member.user_id, 3)

    deviations = await detect_deviation(test_session, member.id)
    post_devs = [d for d in deviations if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) == 0


@pytest.mark.asyncio
async def test_detect_deviation_high_posts(test_session):
    """Spike in posts (>2 std) should trigger deviation alert."""
    group, _ = await make_test_group(test_session, name="Spike", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 2.0, "std": 0.5},
            "avg_messages_per_day": {"mean": 5.0, "std": 2.0},
            "avg_session_duration": {"mean": 30.0, "std": 10.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=40,
    )
    test_session.add(baseline)
    await test_session.flush()

    await _make_spike_posts(test_session, member.user_id, 20)

    deviations = await detect_deviation(test_session, member.id)
    post_devs = [d for d in deviations if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) == 1
    assert post_devs[0]["current_value"] == 20.0
    assert post_devs[0]["baseline_value"] == 2.0
    assert post_devs[0]["std_deviations"] > 2.0


@pytest.mark.asyncio
async def test_detect_deviation_multiple_metrics(test_session):
    """Multiple metrics can deviate simultaneously."""
    group, _ = await make_test_group(test_session, name="Multi", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 1.0, "std": 0.3},
            "avg_messages_per_day": {"mean": 2.0, "std": 0.5},
            "avg_session_duration": {"mean": 20.0, "std": 5.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=30,
    )
    test_session.add(baseline)
    await test_session.flush()

    # Spike posts
    await _make_spike_posts(test_session, member.user_id, 15)

    # Spike messages
    conv = Conversation(id=uuid4(), type="direct", created_by=member.user_id)
    test_session.add(conv)
    await test_session.flush()
    for i in range(30):
        msg = Message(
            id=uuid4(), conversation_id=conv.id, sender_id=member.user_id,
            content=f"Spike msg {i}", message_type="text",
            moderation_status="approved",
        )
        test_session.add(msg)
    await test_session.flush()

    deviations = await detect_deviation(test_session, member.id)
    metric_names = [d["metric"] for d in deviations]
    assert "avg_posts_per_day" in metric_names
    assert "avg_messages_per_day" in metric_names


@pytest.mark.asyncio
async def test_detect_deviation_zero_std(test_session):
    """When std=0 and current > 2x mean, deviation is flagged."""
    group, _ = await make_test_group(test_session, name="ZeroStd", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 2.0, "std": 0.0},
            "avg_messages_per_day": {"mean": 0.0, "std": 0.0},
            "avg_session_duration": {"mean": 0.0, "std": 0.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=14,
    )
    test_session.add(baseline)
    await test_session.flush()

    await _make_spike_posts(test_session, member.user_id, 10)

    deviations = await detect_deviation(test_session, member.id)
    post_devs = [d for d in deviations if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) == 1
    assert post_devs[0]["std_deviations"] == float("inf")


@pytest.mark.asyncio
async def test_detect_deviation_custom_threshold(test_session):
    """Lower threshold should catch smaller deviations."""
    group, _ = await make_test_group(test_session, name="Threshold", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 5.0, "std": 2.0},
            "avg_messages_per_day": {"mean": 10.0, "std": 3.0},
            "avg_session_duration": {"mean": 30.0, "std": 10.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=50,
    )
    test_session.add(baseline)
    await test_session.flush()

    # 10 posts -- 2.5 std from mean (|10-5|/2 = 2.5)
    await _make_spike_posts(test_session, member.user_id, 10)

    # NOT flagged at threshold=3
    devs_high = await detect_deviation(test_session, member.id, threshold=3.0)
    post_devs = [d for d in devs_high if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) == 0

    # Flagged at threshold=1
    devs_low = await detect_deviation(test_session, member.id, threshold=1.0)
    post_devs = [d for d in devs_low if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) == 1


# ---------------------------------------------------------------------------
# update_baselines_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_baselines_batch_no_activity(test_session):
    """Batch update with no active members returns empty."""
    baselines = await update_baselines_batch(test_session, window_days=14)
    assert baselines == []


@pytest.mark.asyncio
async def test_update_baselines_batch_with_activity(test_session):
    """Batch update creates baselines for active members."""
    group, _ = await make_test_group(test_session, name="Batch", group_type="family")
    m1 = await _make_member(test_session, group, name="Child1")
    m2 = await _make_member(test_session, group, name="Child2")

    # Give both members some posts (using their user_ids)
    for member in [m1, m2]:
        for i in range(5):
            post = SocialPost(
                id=uuid4(), author_id=member.user_id,
                content=f"Batch post {i}", post_type="text",
                moderation_status="approved",
            )
            test_session.add(post)
    await test_session.flush()

    baselines = await update_baselines_batch(test_session, window_days=14)
    assert len(baselines) >= 2
    member_ids = {b.member_id for b in baselines}
    assert m1.id in member_ids
    assert m2.id in member_ids


# ---------------------------------------------------------------------------
# get_baseline_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_baseline_summary_no_baseline(test_session):
    """Summary with no baseline returns appropriate message."""
    member_id = uuid4()
    summary = await get_baseline_summary(test_session, member_id)

    assert summary["has_baseline"] is False
    assert "Not enough" in summary["summary"]


@pytest.mark.asyncio
async def test_get_baseline_summary_with_data(test_session):
    """Summary with baseline returns meaningful content."""
    group, _ = await make_test_group(test_session, name="Summary", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 3.5, "std": 1.2},
            "avg_messages_per_day": {"mean": 8.0, "std": 2.5},
            "avg_session_duration": {"mean": 45.0, "std": 12.0},
            "active_hours": [9, 14, 15, 16, 20],
            "content_sentiment_avg": 0.1,
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=60,
    )
    test_session.add(baseline)
    await test_session.flush()

    summary = await get_baseline_summary(test_session, member.id)

    assert summary["has_baseline"] is True
    assert "3.5" in summary["summary"]
    assert "8.0" in summary["summary"]
    assert summary["metrics"]["avg_posts_per_day"] == 3.5
    assert summary["metrics"]["avg_messages_per_day"] == 8.0
    assert summary["metrics"]["avg_session_duration_minutes"] == 45.0
    assert summary["metrics"]["window_days"] == 14
    assert summary["metrics"]["sample_count"] == 60


@pytest.mark.asyncio
async def test_get_baseline_summary_includes_deviations(test_session):
    """Summary includes deviation info when recent activity is anomalous."""
    group, _ = await make_test_group(test_session, name="SumDev", group_type="family")
    member = await _make_member(test_session, group)

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 1.0, "std": 0.3},
            "avg_messages_per_day": {"mean": 5.0, "std": 2.0},
            "avg_session_duration": {"mean": 30.0, "std": 10.0},
            "active_hours": [10, 14],
            "content_sentiment_avg": 0.0,
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=30,
    )
    test_session.add(baseline)
    await test_session.flush()

    await _make_spike_posts(test_session, member.user_id, 20)

    summary = await get_baseline_summary(test_session, member.id)
    assert len(summary["deviations"]) > 0
    assert "unusual patterns" in summary["summary"]
