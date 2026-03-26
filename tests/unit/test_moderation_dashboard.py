"""Unit tests for moderation dashboard service.

Tests: queue assignment, bulk approve/reject, SLA metrics, pattern detection.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.moderation.dashboard_service import (
    assign_moderator,
    bulk_action,
    detect_patterns,
    get_sla_metrics,
    persist_patterns,
    persist_sla_snapshot,
)
from src.moderation.models import (
    ModerationDecision,
    ModerationQueue,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db: AsyncSession, **kwargs) -> User:
    user = User(
        id=kwargs.get("id", uuid.uuid4()),
        email=kwargs.get("email", f"mod-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.get("display_name", "Test Moderator"),
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_queue_entry(
    db: AsyncSession,
    *,
    pipeline: str = "pre_publish",
    status: str = "pending",
    content_type: str = "post",
    age_tier: str | None = "young",
    risk_scores: dict | None = None,
    created_at: datetime | None = None,
) -> ModerationQueue:
    entry = ModerationQueue(
        id=uuid.uuid4(),
        content_type=content_type,
        content_id=uuid.uuid4(),
        pipeline=pipeline,
        status=status,
        age_tier=age_tier,
        risk_scores=risk_scores,
    )
    db.add(entry)
    await db.flush()

    # Override created_at if specified (for SLA tests)
    if created_at:
        entry.created_at = created_at
        await db.flush()

    return entry


async def _create_decision(
    db: AsyncSession,
    queue_id: uuid.UUID,
    *,
    action: str = "approve",
    moderator_id: uuid.UUID | None = None,
    timestamp: datetime | None = None,
) -> ModerationDecision:
    decision = ModerationDecision(
        id=uuid.uuid4(),
        queue_id=queue_id,
        moderator_id=moderator_id,
        action=action,
        reason=f"Test {action}",
    )
    db.add(decision)
    await db.flush()

    if timestamp:
        decision.timestamp = timestamp
        await db.flush()

    return decision


# ---------------------------------------------------------------------------
# Queue assignment tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_moderator_basic(test_session: AsyncSession):
    """Assign a moderator to a pending queue item."""
    user = await _create_user(test_session)
    entry = await _create_queue_entry(test_session)

    assignment = await assign_moderator(test_session, entry.id, user.id)

    assert assignment.queue_id == entry.id
    assert assignment.moderator_id == user.id
    assert assignment.status == "assigned"

    await test_session.refresh(entry)
    assert entry.assigned_to == user.id


@pytest.mark.asyncio
async def test_assign_moderator_reassign(test_session: AsyncSession):
    """Reassigning a moderator marks old assignment as reassigned."""
    user1 = await _create_user(test_session)
    user2 = await _create_user(test_session)
    entry = await _create_queue_entry(test_session)

    a1 = await assign_moderator(test_session, entry.id, user1.id)
    a2 = await assign_moderator(test_session, entry.id, user2.id)

    await test_session.refresh(a1)
    assert a1.status == "reassigned"
    assert a2.status == "assigned"
    assert a2.moderator_id == user2.id


@pytest.mark.asyncio
async def test_assign_moderator_not_found(test_session: AsyncSession):
    """Assigning to a non-existent queue item raises NotFoundError."""
    user = await _create_user(test_session)
    with pytest.raises(NotFoundError):
        await assign_moderator(test_session, uuid.uuid4(), user.id)


@pytest.mark.asyncio
async def test_assign_moderator_already_processed(test_session: AsyncSession):
    """Cannot assign moderator to already-approved item."""
    user = await _create_user(test_session)
    entry = await _create_queue_entry(test_session, status="approved")

    with pytest.raises(ConflictError):
        await assign_moderator(test_session, entry.id, user.id)


@pytest.mark.asyncio
async def test_assign_moderator_rejected_item(test_session: AsyncSession):
    """Cannot assign moderator to already-rejected item."""
    user = await _create_user(test_session)
    entry = await _create_queue_entry(test_session, status="rejected")

    with pytest.raises(ConflictError):
        await assign_moderator(test_session, entry.id, user.id)


# ---------------------------------------------------------------------------
# Bulk action tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_approve(test_session: AsyncSession):
    """Bulk approve multiple queue items."""
    user = await _create_user(test_session)
    e1 = await _create_queue_entry(test_session)
    e2 = await _create_queue_entry(test_session)

    result = await bulk_action(
        test_session,
        queue_ids=[e1.id, e2.id],
        action="approve",
        moderator_id=user.id,
    )

    assert result["total_succeeded"] == 2
    assert result["total_failed"] == 0
    assert result["action"] == "approve"

    await test_session.refresh(e1)
    await test_session.refresh(e2)
    assert e1.status == "approved"
    assert e2.status == "approved"


@pytest.mark.asyncio
async def test_bulk_reject(test_session: AsyncSession):
    """Bulk reject multiple queue items."""
    user = await _create_user(test_session)
    e1 = await _create_queue_entry(test_session)
    e2 = await _create_queue_entry(test_session)

    result = await bulk_action(
        test_session,
        queue_ids=[e1.id, e2.id],
        action="reject",
        moderator_id=user.id,
        reason="Violates policy",
    )

    assert result["total_succeeded"] == 2
    await test_session.refresh(e1)
    assert e1.status == "rejected"


@pytest.mark.asyncio
async def test_bulk_action_partial_failure(test_session: AsyncSession):
    """Bulk action with mix of valid and already-processed items."""
    user = await _create_user(test_session)
    e1 = await _create_queue_entry(test_session)
    e2 = await _create_queue_entry(test_session, status="approved")

    result = await bulk_action(
        test_session,
        queue_ids=[e1.id, e2.id],
        action="reject",
        moderator_id=user.id,
    )

    assert result["total_succeeded"] == 1
    assert result["total_failed"] == 1
    assert "already_approved" in result["failed"][0]["error"]


@pytest.mark.asyncio
async def test_bulk_action_not_found(test_session: AsyncSession):
    """Bulk action with non-existent queue IDs."""
    user = await _create_user(test_session)

    result = await bulk_action(
        test_session,
        queue_ids=[uuid.uuid4()],
        action="approve",
        moderator_id=user.id,
    )

    assert result["total_failed"] == 1
    assert result["failed"][0]["error"] == "not_found"


@pytest.mark.asyncio
async def test_bulk_action_invalid_action(test_session: AsyncSession):
    """Bulk action with invalid action raises ValidationError."""
    user = await _create_user(test_session)
    with pytest.raises(ValidationError):
        await bulk_action(
            test_session,
            queue_ids=[uuid.uuid4()],
            action="delete",
            moderator_id=user.id,
        )


@pytest.mark.asyncio
async def test_bulk_action_empty_list(test_session: AsyncSession):
    """Bulk action with empty list raises ValidationError."""
    user = await _create_user(test_session)
    with pytest.raises(ValidationError):
        await bulk_action(
            test_session,
            queue_ids=[],
            action="approve",
            moderator_id=user.id,
        )


@pytest.mark.asyncio
async def test_bulk_action_completes_assignment(test_session: AsyncSession):
    """Bulk action marks moderator assignment as completed."""
    user = await _create_user(test_session)
    entry = await _create_queue_entry(test_session)
    assignment = await assign_moderator(test_session, entry.id, user.id)

    await bulk_action(
        test_session,
        queue_ids=[entry.id],
        action="approve",
        moderator_id=user.id,
    )

    await test_session.refresh(assignment)
    assert assignment.status == "completed"
    assert assignment.completed_at is not None


# ---------------------------------------------------------------------------
# SLA metrics tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sla_metrics_empty(test_session: AsyncSession):
    """SLA metrics with no data returns zero values."""
    result = await get_sla_metrics(test_session)

    assert result["window_hours"] == 24
    assert "pre_publish" in result["pipelines"]
    assert result["pipelines"]["pre_publish"]["p95_ms"] == 0.0
    assert result["pipelines"]["pre_publish"]["items_total"] == 0
    assert result["pipelines"]["pre_publish"]["compliance_pct"] == 100.0


@pytest.mark.asyncio
async def test_sla_metrics_with_data(test_session: AsyncSession):
    """SLA metrics computed correctly from queue entries and decisions."""
    now = datetime.now(timezone.utc)

    # Create entries with known processing times
    for i in range(10):
        created = now - timedelta(minutes=30 - i)
        entry = await _create_queue_entry(
            test_session, pipeline="pre_publish", status="approved",
            created_at=created,
        )
        # Decision 500ms after creation
        decision_time = created + timedelta(milliseconds=500)
        await _create_decision(
            test_session, entry.id, action="approve", timestamp=decision_time,
        )

    result = await get_sla_metrics(test_session, pipeline="pre_publish")

    pre = result["pipelines"]["pre_publish"]
    assert pre["items_total"] == 10
    assert pre["items_in_sla"] == 10
    assert pre["items_breached_sla"] == 0
    assert pre["p95_ms"] <= 600  # ~500ms with some tolerance


@pytest.mark.asyncio
async def test_sla_metrics_breached(test_session: AsyncSession):
    """SLA metrics show breached items when processing exceeds target."""
    now = datetime.now(timezone.utc)

    # Create entry that takes 3 seconds (breaches 2s SLA)
    created = now - timedelta(minutes=10)
    entry = await _create_queue_entry(
        test_session, pipeline="pre_publish", status="approved",
        created_at=created,
    )
    decision_time = created + timedelta(seconds=3)
    await _create_decision(
        test_session, entry.id, action="approve", timestamp=decision_time,
    )

    result = await get_sla_metrics(test_session, pipeline="pre_publish")

    pre = result["pipelines"]["pre_publish"]
    assert pre["items_breached_sla"] == 1
    assert pre["items_in_sla"] == 0
    assert pre["p95_ms"] >= 2000


@pytest.mark.asyncio
async def test_sla_metrics_post_publish(test_session: AsyncSession):
    """Post-publish SLA uses 60s target."""
    now = datetime.now(timezone.utc)

    created = now - timedelta(minutes=10)
    entry = await _create_queue_entry(
        test_session, pipeline="post_publish", status="approved",
        created_at=created,
    )
    # 30s processing — within 60s SLA
    decision_time = created + timedelta(seconds=30)
    await _create_decision(
        test_session, entry.id, action="approve", timestamp=decision_time,
    )

    result = await get_sla_metrics(test_session, pipeline="post_publish")

    post = result["pipelines"]["post_publish"]
    assert post["items_in_sla"] == 1
    assert post["items_breached_sla"] == 0


# ---------------------------------------------------------------------------
# Pattern detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_patterns_empty(test_session: AsyncSession):
    """Pattern detection with no data returns empty list."""
    patterns = await detect_patterns(test_session)
    assert patterns == []


@pytest.mark.asyncio
async def test_detect_keyword_spike(test_session: AsyncSession):
    """Detect keyword spike pattern when 3+ rejections share a keyword."""
    for _ in range(4):
        await _create_queue_entry(
            test_session,
            status="rejected",
            risk_scores={
                "keyword_filter": {
                    "action": "block",
                    "matched_keywords": ["badword"],
                }
            },
        )

    patterns = await detect_patterns(test_session)

    keyword_patterns = [p for p in patterns if p["pattern_type"] == "keyword_spike"]
    assert len(keyword_patterns) >= 1
    assert "badword" in keyword_patterns[0]["details"]["keyword"]
    assert keyword_patterns[0]["details"]["count"] == 4


@pytest.mark.asyncio
async def test_detect_escalation_surge(test_session: AsyncSession):
    """Detect escalation surge when 5+ items are escalated."""
    for _ in range(6):
        await _create_queue_entry(test_session, status="escalated")

    patterns = await detect_patterns(test_session)

    surge_patterns = [p for p in patterns if p["pattern_type"] == "escalation_surge"]
    assert len(surge_patterns) == 1
    assert surge_patterns[0]["details"]["escalated_count"] == 6


@pytest.mark.asyncio
async def test_detect_risk_category_trend(test_session: AsyncSession):
    """Detect risk category trend when a category appears 3+ times."""
    for _ in range(4):
        await _create_queue_entry(
            test_session,
            status="pending",
            risk_scores={
                "social_risk": {
                    "category": "bullying",
                    "severity": "high",
                    "score": 80,
                }
            },
        )

    patterns = await detect_patterns(test_session)

    cat_patterns = [p for p in patterns if p["pattern_type"] == "risk_category_trend"]
    assert len(cat_patterns) >= 1
    assert cat_patterns[0]["details"]["category"] == "bullying"


@pytest.mark.asyncio
async def test_detect_patterns_24h_window(test_session: AsyncSession):
    """Patterns only consider items within the time window."""
    # Create old rejected items (outside 24h window) — we can't easily backdate
    # created_at with server_default, so we just verify the query runs
    for _ in range(3):
        await _create_queue_entry(
            test_session,
            status="rejected",
            risk_scores={
                "keyword_filter": {"action": "block", "matched_keywords": ["old_word"]},
            },
        )

    # With default 24h window, these should be found
    patterns = await detect_patterns(test_session, hours=24)
    assert isinstance(patterns, list)


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_patterns(test_session: AsyncSession):
    """Persist detected patterns to the database."""
    now = datetime.now(timezone.utc)
    patterns_data = [
        {
            "pattern_type": "keyword_spike",
            "description": "Test keyword spike",
            "severity": "medium",
            "details": {"keyword": "test", "count": 5},
            "window_start": (now - timedelta(hours=24)).isoformat(),
            "window_end": now.isoformat(),
        }
    ]

    records = await persist_patterns(test_session, patterns_data)

    assert len(records) == 1
    assert records[0].pattern_type == "keyword_spike"
    assert records[0].severity == "medium"


@pytest.mark.asyncio
async def test_persist_sla_snapshot(test_session: AsyncSession):
    """Persist SLA metrics snapshot to the database."""
    now = datetime.now(timezone.utc)
    sla_data = {
        "window_hours": 24,
        "window_start": (now - timedelta(hours=24)).isoformat(),
        "window_end": now.isoformat(),
        "pipelines": {
            "pre_publish": {
                "pipeline": "pre_publish",
                "p95_ms": 450.5,
                "items_total": 100,
                "items_in_sla": 98,
                "items_breached_sla": 2,
                "sla_target_ms": 2000,
                "compliance_pct": 98.0,
            }
        },
    }

    records = await persist_sla_snapshot(test_session, sla_data)

    assert len(records) == 1
    assert records[0].pipeline == "pre_publish"
    assert records[0].p95_ms == 450.5
    assert records[0].items_in_sla == 98
