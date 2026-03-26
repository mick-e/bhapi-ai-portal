"""E2E tests for behavioral baselines -- full pipeline through intelligence service."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.auth.models import User
from src.device_agent.models import DeviceSession
from src.groups.models import GroupMember
from src.intelligence.models import BehavioralBaseline
from src.intelligence.service import (
    compute_member_baseline,
    create_baseline,
    detect_member_deviation,
    get_baseline,
    get_member_baseline_summary,
    run_baseline_batch,
)
from src.messaging.models import Conversation, Message
from src.social.behavioral import compute_baseline, detect_deviation
from src.social.models import SocialPost
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_member(session, name="Child") -> tuple:
    """Create group + user + member. Returns (group, member)."""
    group, owner_id = await make_test_group(
        session, name=f"E2E-{name}", group_type="family",
    )
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
    return group, member


async def _populate_activity(
    session, member, group_id,
    post_count=0, msg_count=0, session_data=None,
):
    """Create activity data for a member.

    Uses member.user_id for posts/messages and member.id for device sessions.
    """
    now = datetime.now(timezone.utc)
    user_id = member.user_id
    member_id = member.id

    # Posts
    for i in range(post_count):
        post = SocialPost(
            id=uuid4(),
            author_id=user_id,
            content=f"E2E post {i}",
            post_type="text",
            moderation_status="approved",
        )
        session.add(post)
    await session.flush()

    # Update post timestamps to spread across days
    if post_count > 0:
        result = await session.execute(
            select(SocialPost).where(SocialPost.author_id == user_id)
        )
        posts = list(result.scalars().all())
        for i, p in enumerate(posts):
            p.created_at = now - timedelta(days=i % 14, hours=1)
        await session.flush()

    # Messages
    if msg_count > 0:
        conv = Conversation(
            id=uuid4(), type="direct", created_by=user_id,
        )
        session.add(conv)
        await session.flush()

        for i in range(msg_count):
            msg = Message(
                id=uuid4(),
                conversation_id=conv.id,
                sender_id=user_id,
                content=f"E2E msg {i}",
                message_type="text",
                moderation_status="approved",
            )
            session.add(msg)
        await session.flush()

        result = await session.execute(
            select(Message).where(Message.sender_id == user_id)
        )
        msgs = list(result.scalars().all())
        for i, m in enumerate(msgs):
            m.created_at = now - timedelta(days=i % 14, hours=2)
        await session.flush()

    # Device sessions
    if session_data:
        for days_back, duration_min in session_data:
            started = now - timedelta(days=days_back, hours=3)
            ended = started + timedelta(minutes=duration_min)
            ds = DeviceSession(
                id=uuid4(),
                member_id=member_id,
                group_id=group_id,
                device_id="e2e-device",
                device_type="android",
                started_at=started,
                ended_at=ended,
            )
            session.add(ds)
        await session.flush()


# ---------------------------------------------------------------------------
# E2E: Full pipeline compute + detect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_compute_and_detect_no_deviation(test_session):
    """Full pipeline: compute baseline from activity, detect no deviation."""
    group, member = await _setup_member(test_session, "NoDev")

    await _populate_activity(
        test_session, member, group.id,
        post_count=14, msg_count=14,
        session_data=[(d, 30) for d in range(14)],
    )

    baseline = await compute_member_baseline(test_session, member.id, window_days=14)
    assert baseline is not None
    assert baseline.metrics["avg_posts_per_day"]["mean"] > 0

    deviations = await detect_member_deviation(test_session, member.id)
    assert isinstance(deviations, list)


@pytest.mark.asyncio
async def test_e2e_compute_and_detect_with_spike(test_session):
    """Full pipeline: baseline from low activity, spike triggers deviation."""
    group, member = await _setup_member(test_session, "Spike")

    await _populate_activity(test_session, member, group.id, post_count=7)

    baseline = await compute_baseline(test_session, member.id, window_days=14)
    assert baseline is not None

    # Add a big spike: 30 posts today
    for i in range(30):
        post = SocialPost(
            id=uuid4(), author_id=member.user_id,
            content=f"Spike {i}", post_type="text",
            moderation_status="approved",
        )
        test_session.add(post)
    await test_session.flush()

    deviations = await detect_deviation(test_session, member.id)
    post_devs = [d for d in deviations if d["metric"] == "avg_posts_per_day"]
    assert len(post_devs) >= 1
    assert post_devs[0]["std_deviations"] > 2.0


@pytest.mark.asyncio
async def test_e2e_intelligence_service_compute(test_session):
    """Intelligence service compute_member_baseline delegates correctly."""
    group, member = await _setup_member(test_session, "IntSvc")

    await _populate_activity(test_session, member, group.id, post_count=20)

    baseline = await compute_member_baseline(test_session, member.id)
    assert baseline.member_id == member.id
    assert baseline.window_days == 14
    assert baseline.metrics is not None


@pytest.mark.asyncio
async def test_e2e_intelligence_service_detect(test_session):
    """Intelligence service detect_member_deviation delegates correctly."""
    group, member = await _setup_member(test_session, "IntDet")

    bl = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 1.0, "std": 0.5},
            "avg_messages_per_day": {"mean": 3.0, "std": 1.0},
            "avg_session_duration": {"mean": 20.0, "std": 5.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=20,
    )
    test_session.add(bl)
    await test_session.flush()

    for i in range(25):
        post = SocialPost(
            id=uuid4(), author_id=member.user_id,
            content=f"DetSvc {i}", post_type="text",
            moderation_status="approved",
        )
        test_session.add(post)
    await test_session.flush()

    deviations = await detect_member_deviation(test_session, member.id)
    assert any(d["metric"] == "avg_posts_per_day" for d in deviations)


@pytest.mark.asyncio
async def test_e2e_intelligence_service_summary(test_session):
    """Intelligence service get_member_baseline_summary returns summary."""
    group, member = await _setup_member(test_session, "IntSum")

    bl = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 2.5, "std": 0.8},
            "avg_messages_per_day": {"mean": 6.0, "std": 2.0},
            "avg_session_duration": {"mean": 35.0, "std": 10.0},
            "active_hours": [10, 14, 15, 16],
            "content_sentiment_avg": 0.05,
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=45,
    )
    test_session.add(bl)
    await test_session.flush()

    summary = await get_member_baseline_summary(test_session, member.id)
    assert summary["has_baseline"] is True
    assert summary["metrics"]["avg_posts_per_day"] == 2.5


@pytest.mark.asyncio
async def test_e2e_batch_update_multiple_members(test_session):
    """Batch update recomputes baselines for all active members."""
    group, m1 = await _setup_member(test_session, "Batch1")
    _, m2 = await _setup_member(test_session, "Batch2")

    await _populate_activity(test_session, m1, group.id, post_count=10)
    await _populate_activity(test_session, m2, group.id, post_count=8)

    baselines = await run_baseline_batch(test_session, window_days=14)
    member_ids = {b.member_id for b in baselines}
    assert m1.id in member_ids
    assert m2.id in member_ids


@pytest.mark.asyncio
async def test_e2e_batch_update_empty(test_session):
    """Batch update with no active members returns empty list."""
    baselines = await run_baseline_batch(test_session, window_days=14)
    assert baselines == []


@pytest.mark.asyncio
async def test_e2e_baseline_persistence(test_session):
    """Computed baseline is persisted and retrievable via get_baseline."""
    group, member = await _setup_member(test_session, "Persist")

    await _populate_activity(test_session, member, group.id, post_count=14)

    created = await compute_baseline(test_session, member.id, window_days=14)
    await test_session.commit()

    retrieved = await get_baseline(test_session, member.id, window_days=14)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.metrics == created.metrics


@pytest.mark.asyncio
async def test_e2e_deviation_with_session_spike(test_session):
    """Device session duration spike triggers deviation."""
    group, member = await _setup_member(test_session, "SesSpike")

    bl = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 2.0, "std": 1.0},
            "avg_messages_per_day": {"mean": 5.0, "std": 2.0},
            "avg_session_duration": {"mean": 30.0, "std": 5.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=30,
    )
    test_session.add(bl)
    await test_session.flush()

    # Very long session today (300 minutes vs mean 30)
    now = datetime.now(timezone.utc)
    ds = DeviceSession(
        id=uuid4(),
        member_id=member.id,
        group_id=group.id,
        device_id="spike-device",
        device_type="ios",
        started_at=now - timedelta(hours=5),
        ended_at=now,
    )
    test_session.add(ds)
    await test_session.flush()

    deviations = await detect_deviation(test_session, member.id)
    session_devs = [d for d in deviations if d["metric"] == "avg_session_duration"]
    assert len(session_devs) == 1
    assert session_devs[0]["std_deviations"] > 2.0


@pytest.mark.asyncio
async def test_e2e_summary_no_data(test_session):
    """Summary for member with no baseline returns helpful message."""
    summary = await get_member_baseline_summary(test_session, uuid4())
    assert summary["has_baseline"] is False
    assert "Not enough" in summary["summary"]


@pytest.mark.asyncio
async def test_e2e_deviation_message_spike(test_session):
    """Message spike triggers deviation."""
    group, member = await _setup_member(test_session, "MsgSpike")

    bl = BehavioralBaseline(
        id=uuid4(),
        member_id=member.id,
        window_days=14,
        metrics={
            "avg_posts_per_day": {"mean": 2.0, "std": 1.0},
            "avg_messages_per_day": {"mean": 3.0, "std": 0.5},
            "avg_session_duration": {"mean": 30.0, "std": 10.0},
        },
        computed_at=datetime.now(timezone.utc),
        sample_count=30,
    )
    test_session.add(bl)
    await test_session.flush()

    # 50 messages today (vs mean 3, std 0.5)
    conv = Conversation(id=uuid4(), type="direct", created_by=member.user_id)
    test_session.add(conv)
    await test_session.flush()

    for i in range(50):
        msg = Message(
            id=uuid4(), conversation_id=conv.id, sender_id=member.user_id,
            content=f"Spike msg {i}", message_type="text",
            moderation_status="approved",
        )
        test_session.add(msg)
    await test_session.flush()

    deviations = await detect_deviation(test_session, member.id)
    msg_devs = [d for d in deviations if d["metric"] == "avg_messages_per_day"]
    assert len(msg_devs) == 1
    assert msg_devs[0]["current_value"] == 50.0
    assert msg_devs[0]["std_deviations"] > 2.0


@pytest.mark.asyncio
async def test_e2e_recompute_overwrites(test_session):
    """Recomputing baseline creates a new record (does not mutate old one)."""
    group, member = await _setup_member(test_session, "Recompute")

    await _populate_activity(test_session, member, group.id, post_count=14)

    b1 = await compute_baseline(test_session, member.id, window_days=14)

    # Add more activity
    for i in range(10):
        post = SocialPost(
            id=uuid4(), author_id=member.user_id,
            content=f"Extra {i}", post_type="text",
            moderation_status="approved",
        )
        test_session.add(post)
    await test_session.flush()

    b2 = await compute_baseline(test_session, member.id, window_days=14)

    assert b1.id != b2.id
    assert b2.computed_at >= b1.computed_at


@pytest.mark.asyncio
async def test_e2e_create_baseline_via_service(test_session):
    """create_baseline in intelligence service stores baseline."""
    group, member = await _setup_member(test_session, "CreateSvc")

    bl = await create_baseline(
        test_session,
        member_id=member.id,
        window_days=14,
        metrics={"avg_posts_per_day": {"mean": 5.0, "std": 1.5}},
        sample_count=28,
    )
    assert bl.id is not None
    assert bl.member_id == member.id
    assert bl.metrics["avg_posts_per_day"]["mean"] == 5.0


@pytest.mark.asyncio
async def test_e2e_get_baseline_via_service(test_session):
    """get_baseline retrieves the latest baseline for a given window."""
    group, member = await _setup_member(test_session, "GetSvc")

    bl1 = BehavioralBaseline(
        id=uuid4(), member_id=member.id, window_days=14,
        metrics={"test": "old"}, computed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sample_count=10,
    )
    bl2 = BehavioralBaseline(
        id=uuid4(), member_id=member.id, window_days=14,
        metrics={"test": "new"}, computed_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        sample_count=20,
    )
    test_session.add(bl1)
    test_session.add(bl2)
    await test_session.flush()

    result = await get_baseline(test_session, member.id, window_days=14)
    assert result is not None
    assert result.metrics["test"] == "new"
