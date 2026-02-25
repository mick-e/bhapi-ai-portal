"""E2E tests for enriched activity API (list_events_enriched).

Covers enrichment with member_name and risk_level, pagination,
filtering by platform / event_type / risk_level / search, and
the empty-group edge case.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.models import User
from src.capture.models import CaptureEvent
from src.capture.service import list_events_enriched
from src.database import Base
from src.groups.models import Group, GroupMember
from src.risk.models import RiskEvent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    yield session

    await session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session):
    """Seed a user, group, member, capture events, and risk events.

    Returns a dict with all IDs and the session for convenient access.

    Capture events (newest first by timestamp):
      0 - chatgpt / prompt   / "Tell me about quantum physics"     (has HIGH risk)
      1 - gemini  / response / "Here is the answer about biology"  (has MEDIUM risk)
      2 - claude  / prompt   / "Write a story about a dragon"      (no risk -> defaults low)
      3 - chatgpt / response / "Photosynthesis is the process..."  (no risk -> defaults low)
      4 - copilot / prompt   / "Help me with my math homework"     (no risk -> defaults low)
    """
    now = datetime.now(timezone.utc)

    # --- User ---
    user_id = uuid4()
    user = User(
        id=user_id,
        email="enriched@test.com",
        display_name="Test Parent",
        account_type="family",
        password_hash="pbkdf2:sha256:fakehash",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    # --- Group ---
    group_id = uuid4()
    group = Group(
        id=group_id,
        name="Enriched Test Family",
        type="family",
        owner_id=user_id,
    )
    db_session.add(group)
    await db_session.flush()

    # --- Group Member ---
    member_id = uuid4()
    member = GroupMember(
        id=member_id,
        group_id=group_id,
        user_id=user_id,
        role="member",
        display_name="Alice",
    )
    db_session.add(member)
    await db_session.flush()

    # --- Capture Events (5 events, timestamps descending) ---
    events_data = [
        {
            "platform": "chatgpt",
            "event_type": "prompt",
            "content": "Tell me about quantum physics",
            "delta_minutes": 0,
        },
        {
            "platform": "gemini",
            "event_type": "response",
            "content": "Here is the answer about biology",
            "delta_minutes": -10,
        },
        {
            "platform": "claude",
            "event_type": "prompt",
            "content": "Write a story about a dragon",
            "delta_minutes": -20,
        },
        {
            "platform": "chatgpt",
            "event_type": "response",
            "content": "Photosynthesis is the process of converting light",
            "delta_minutes": -30,
        },
        {
            "platform": "copilot",
            "event_type": "prompt",
            "content": "Help me with my math homework",
            "delta_minutes": -40,
        },
    ]

    capture_events = []
    for i, ed in enumerate(events_data):
        ce = CaptureEvent(
            id=uuid4(),
            group_id=group_id,
            member_id=member_id,
            platform=ed["platform"],
            session_id=f"sess-{i:03d}",
            event_type=ed["event_type"],
            timestamp=now + timedelta(minutes=ed["delta_minutes"]),
            content=ed["content"],
            risk_processed=False,
            source_channel="extension",
        )
        db_session.add(ce)
        capture_events.append(ce)

    await db_session.flush()

    # --- Risk Events (linked to capture events 0 and 1) ---
    risk_high = RiskEvent(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        capture_event_id=capture_events[0].id,
        category="unsafe_content",
        severity="high",
        confidence=0.92,
    )
    risk_medium = RiskEvent(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        capture_event_id=capture_events[1].id,
        category="pii_detected",
        severity="medium",
        confidence=0.75,
    )
    db_session.add_all([risk_high, risk_medium])
    await db_session.flush()

    # --- Empty group (for empty-result tests) ---
    empty_group_id = uuid4()
    empty_group = Group(
        id=empty_group_id,
        name="Empty Family",
        type="family",
        owner_id=user_id,
    )
    db_session.add(empty_group)
    await db_session.flush()

    return {
        "session": db_session,
        "user_id": user_id,
        "group_id": group_id,
        "member_id": member_id,
        "empty_group_id": empty_group_id,
        "capture_events": capture_events,
        "risk_high": risk_high,
        "risk_medium": risk_medium,
    }


# ---------------------------------------------------------------------------
# Test 1: Enriched events include member_name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enriched_events_include_member_name(seed_data):
    """Enriched items should include the member's display_name."""
    data = seed_data
    result = await list_events_enriched(
        data["session"], data["group_id"]
    )
    assert len(result["items"]) == 5
    for item in result["items"]:
        assert item.member_name == "Alice"


# ---------------------------------------------------------------------------
# Test 2: Risk level from linked RiskEvent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enriched_events_include_risk_level(seed_data):
    """Events linked to a RiskEvent should return its severity as risk_level.

    Event 0 -> high, Event 1 -> medium, Events 2-4 -> low (default).
    """
    data = seed_data
    result = await list_events_enriched(
        data["session"], data["group_id"]
    )
    items = result["items"]

    # Items are ordered by timestamp DESC, so event 0 is first
    risk_by_event_id = {item.id: item.risk_level for item in items}

    assert risk_by_event_id[data["capture_events"][0].id] == "high"
    assert risk_by_event_id[data["capture_events"][1].id] == "medium"
    assert risk_by_event_id[data["capture_events"][2].id] == "low"
    assert risk_by_event_id[data["capture_events"][3].id] == "low"
    assert risk_by_event_id[data["capture_events"][4].id] == "low"

    # Also verify flagged field
    flagged_by_id = {item.id: item.flagged for item in items}
    assert flagged_by_id[data["capture_events"][0].id] is True   # high -> flagged
    assert flagged_by_id[data["capture_events"][1].id] is False  # medium -> not flagged
    assert flagged_by_id[data["capture_events"][2].id] is False  # low -> not flagged


# ---------------------------------------------------------------------------
# Test 3: Pagination (page, page_size, total, total_pages)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_fields(seed_data):
    """Paginated response includes correct total, page, page_size, total_pages."""
    data = seed_data

    # Page 1 with page_size=2
    result = await list_events_enriched(
        data["session"], data["group_id"], page=1, page_size=2
    )
    assert result["total"] == 5
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_pages"] == 3  # ceil(5/2)
    assert len(result["items"]) == 2

    # Page 2
    result2 = await list_events_enriched(
        data["session"], data["group_id"], page=2, page_size=2
    )
    assert result2["page"] == 2
    assert len(result2["items"]) == 2

    # Page 3 (last page, only 1 item)
    result3 = await list_events_enriched(
        data["session"], data["group_id"], page=3, page_size=2
    )
    assert result3["page"] == 3
    assert len(result3["items"]) == 1

    # Ensure no overlap between pages
    all_ids = (
        [i.id for i in result["items"]]
        + [i.id for i in result2["items"]]
        + [i.id for i in result3["items"]]
    )
    assert len(set(all_ids)) == 5


@pytest.mark.asyncio
async def test_pagination_beyond_last_page(seed_data):
    """Requesting a page beyond the last returns empty items but correct metadata."""
    data = seed_data
    result = await list_events_enriched(
        data["session"], data["group_id"], page=100, page_size=20
    )
    assert result["items"] == []
    assert result["total"] == 5
    assert result["page"] == 100
    assert result["total_pages"] == 1  # ceil(5/20) = 1


# ---------------------------------------------------------------------------
# Test 4: Filter by platform
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filter_by_platform(seed_data):
    """Filter by platform returns only matching events."""
    data = seed_data

    # chatgpt -> events 0 and 3
    result = await list_events_enriched(
        data["session"], data["group_id"], platform="chatgpt"
    )
    assert result["total"] == 2
    assert len(result["items"]) == 2
    for item in result["items"]:
        assert item.provider == "chatgpt"

    # claude -> event 2 only
    result2 = await list_events_enriched(
        data["session"], data["group_id"], platform="claude"
    )
    assert result2["total"] == 1
    assert result2["items"][0].provider == "claude"

    # grok -> none
    result3 = await list_events_enriched(
        data["session"], data["group_id"], platform="grok"
    )
    assert result3["total"] == 0
    assert result3["items"] == []


# ---------------------------------------------------------------------------
# Test 5: Filter by event_type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filter_by_event_type(seed_data):
    """Filter by event_type returns only matching events."""
    data = seed_data

    # prompt -> events 0, 2, 4
    result = await list_events_enriched(
        data["session"], data["group_id"], event_type="prompt"
    )
    assert result["total"] == 3
    for item in result["items"]:
        assert item.event_type == "prompt"

    # response -> events 1, 3
    result2 = await list_events_enriched(
        data["session"], data["group_id"], event_type="response"
    )
    assert result2["total"] == 2
    for item in result2["items"]:
        assert item.event_type == "response"


# ---------------------------------------------------------------------------
# Test 6: Filter by risk_level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filter_by_risk_level(seed_data):
    """Filter by risk_level post-filters enriched items."""
    data = seed_data

    # high -> only event 0
    result = await list_events_enriched(
        data["session"], data["group_id"], risk_level="high"
    )
    assert len(result["items"]) == 1
    assert result["items"][0].risk_level == "high"
    assert result["items"][0].id == data["capture_events"][0].id

    # medium -> only event 1
    result2 = await list_events_enriched(
        data["session"], data["group_id"], risk_level="medium"
    )
    assert len(result2["items"]) == 1
    assert result2["items"][0].risk_level == "medium"
    assert result2["items"][0].id == data["capture_events"][1].id

    # low -> events 2, 3, 4
    result3 = await list_events_enriched(
        data["session"], data["group_id"], risk_level="low"
    )
    assert len(result3["items"]) == 3
    for item in result3["items"]:
        assert item.risk_level == "low"

    # critical -> none (no critical risk events seeded)
    result4 = await list_events_enriched(
        data["session"], data["group_id"], risk_level="critical"
    )
    assert len(result4["items"]) == 0


# ---------------------------------------------------------------------------
# Test 7: Search query (content ilike match)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_query_content_match(seed_data):
    """Search query filters events by content (case-insensitive partial match)."""
    data = seed_data

    # "quantum" matches event 0 only
    result = await list_events_enriched(
        data["session"], data["group_id"], search="quantum"
    )
    assert result["total"] == 1
    assert result["items"][0].id == data["capture_events"][0].id

    # "DRAGON" (case-insensitive) matches event 2
    result2 = await list_events_enriched(
        data["session"], data["group_id"], search="DRAGON"
    )
    assert result2["total"] == 1
    assert result2["items"][0].id == data["capture_events"][2].id

    # "math homework" matches event 4
    result3 = await list_events_enriched(
        data["session"], data["group_id"], search="math homework"
    )
    assert result3["total"] == 1
    assert result3["items"][0].id == data["capture_events"][4].id

    # "nonexistent" matches nothing
    result4 = await list_events_enriched(
        data["session"], data["group_id"], search="nonexistent"
    )
    assert result4["total"] == 0
    assert result4["items"] == []


@pytest.mark.asyncio
async def test_search_combined_with_platform_filter(seed_data):
    """Search + platform filter are applied together."""
    data = seed_data

    # "about" matches events 0 ("quantum physics") and 1 ("about biology")
    # But filtering platform=chatgpt limits to event 0 only
    result = await list_events_enriched(
        data["session"], data["group_id"], platform="chatgpt", search="about"
    )
    assert result["total"] == 1
    assert result["items"][0].id == data["capture_events"][0].id


# ---------------------------------------------------------------------------
# Test 8: Empty group returns empty items
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_group_returns_empty_items(seed_data):
    """A group with no capture events returns an empty items list."""
    data = seed_data
    result = await list_events_enriched(
        data["session"], data["empty_group_id"]
    )
    assert result["items"] == []
    assert result["total"] == 0
    assert result["page"] == 1
    assert result["page_size"] == 20
    assert result["total_pages"] == 1
