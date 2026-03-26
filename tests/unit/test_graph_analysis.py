"""Unit tests for social graph analysis and intelligence module."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.intelligence.models import SocialGraphEdge
from src.intelligence.schemas import (
    AbuseSignalCreate,
    SocialGraphEdgeCreate,
)
from src.intelligence.service import (
    create_abuse_signal,
    create_baseline,
    create_graph_edge,
    get_abuse_signals,
    get_baseline,
    get_member_edges,
    resolve_abuse_signal,
    run_age_pattern_check,
    run_graph_analysis,
    run_influence_mapping,
    run_isolation_check,
)
from src.social.graph_analysis import _age_to_tier, _calculate_age

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(session, **kwargs):
    """Helper to create a User."""
    user = User(
        id=kwargs.get("id", uuid.uuid4()),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name=kwargs.get("display_name", "Test User"),
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    return user


def _make_member(session, group_id, **kwargs):
    """Helper to create a GroupMember."""
    member = GroupMember(
        id=kwargs.get("id", uuid.uuid4()),
        group_id=group_id,
        user_id=kwargs.get("user_id"),
        role=kwargs.get("role", "member"),
        display_name=kwargs.get("display_name", "Child"),
        date_of_birth=kwargs.get("date_of_birth"),
    )
    session.add(member)
    return member


@pytest_asyncio.fixture
async def graph_data(test_session: AsyncSession):
    """Create a family with multiple children of different ages for graph tests."""
    user = _make_user(test_session, display_name="Parent")
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    # Child aged 7 (young tier)
    child_7 = _make_member(
        test_session, group.id,
        display_name="Child 7yo",
        date_of_birth=datetime(2019, 3, 15, tzinfo=timezone.utc),
    )
    # Child aged 10 (preteen tier)
    child_10 = _make_member(
        test_session, group.id,
        display_name="Child 10yo",
        date_of_birth=datetime(2016, 6, 20, tzinfo=timezone.utc),
    )
    # Child aged 15 (teen tier)
    child_15 = _make_member(
        test_session, group.id,
        display_name="Child 15yo",
        date_of_birth=datetime(2011, 1, 10, tzinfo=timezone.utc),
    )
    # Child aged 13 (teen tier)
    child_13 = _make_member(
        test_session, group.id,
        display_name="Child 13yo",
        date_of_birth=datetime(2013, 8, 5, tzinfo=timezone.utc),
    )
    # Child aged 8 (young tier)
    child_8 = _make_member(
        test_session, group.id,
        display_name="Child 8yo",
        date_of_birth=datetime(2018, 4, 12, tzinfo=timezone.utc),
    )

    await test_session.flush()

    return {
        "user": user,
        "group": group,
        "child_7": child_7,
        "child_10": child_10,
        "child_15": child_15,
        "child_13": child_13,
        "child_8": child_8,
    }


# ---------------------------------------------------------------------------
# Age Calculation / Tier Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_age_valid():
    """_calculate_age returns correct age for a known DOB."""
    dob = datetime(2019, 3, 15, tzinfo=timezone.utc)
    age = _calculate_age(dob)
    assert age == 7 or age == 6  # depends on current date vs birthday


@pytest.mark.asyncio
async def test_calculate_age_none():
    """_calculate_age returns None for None DOB."""
    assert _calculate_age(None) is None


@pytest.mark.asyncio
async def test_age_to_tier_young():
    """Young children map to 'young' tier."""
    assert _age_to_tier(5) == "young"
    assert _age_to_tier(9) == "young"


@pytest.mark.asyncio
async def test_age_to_tier_preteen():
    """Preteens map to 'preteen' tier."""
    assert _age_to_tier(10) == "preteen"
    assert _age_to_tier(12) == "preteen"


@pytest.mark.asyncio
async def test_age_to_tier_teen():
    """Teens map to 'teen' tier."""
    assert _age_to_tier(13) == "teen"
    assert _age_to_tier(15) == "teen"
    assert _age_to_tier(16) == "teen"


# ---------------------------------------------------------------------------
# Graph Edge Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_graph_edge(test_session: AsyncSession, graph_data):
    """Create a social graph edge between two members."""
    data = SocialGraphEdgeCreate(
        source_id=graph_data["child_7"].id,
        target_id=graph_data["child_10"].id,
        edge_type="contact",
        weight=1.0,
    )
    edge = await create_graph_edge(test_session, data)
    assert edge.id is not None
    assert edge.source_id == graph_data["child_7"].id
    assert edge.target_id == graph_data["child_10"].id
    assert edge.edge_type == "contact"


@pytest.mark.asyncio
async def test_create_graph_edge_self_loop(test_session: AsyncSession, graph_data):
    """Creating an edge from a member to themselves raises ValidationError."""
    data = SocialGraphEdgeCreate(
        source_id=graph_data["child_7"].id,
        target_id=graph_data["child_7"].id,
        edge_type="contact",
    )
    with pytest.raises(ValidationError):
        await create_graph_edge(test_session, data)


@pytest.mark.asyncio
async def test_create_graph_edge_message(test_session: AsyncSession, graph_data):
    """Create a message-type edge."""
    data = SocialGraphEdgeCreate(
        source_id=graph_data["child_13"].id,
        target_id=graph_data["child_15"].id,
        edge_type="message",
        weight=2.0,
        last_interaction=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
    )
    edge = await create_graph_edge(test_session, data)
    assert edge.edge_type == "message"
    assert edge.weight == 2.0
    assert edge.last_interaction is not None


@pytest.mark.asyncio
async def test_get_member_edges(test_session: AsyncSession, graph_data):
    """Get edges for a member returns correct count."""
    for target_key in ["child_10", "child_13"]:
        data = SocialGraphEdgeCreate(
            source_id=graph_data["child_7"].id,
            target_id=graph_data[target_key].id,
            edge_type="contact",
        )
        await create_graph_edge(test_session, data)

    edges, total = await get_member_edges(test_session, graph_data["child_7"].id)
    assert total == 2
    assert len(edges) == 2


# ---------------------------------------------------------------------------
# Age-Inappropriate Contact Detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_age_inappropriate_contact(test_session: AsyncSession, graph_data):
    """Flag when contact age gap exceeds threshold (15yo contacts 7yo = 8yr gap)."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_15"].id,
        target_id=graph_data["child_7"].id,
        edge_type="contact",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_graph_analysis(test_session, graph_data["child_15"].id)
    assert result["flagged_count"] >= 1
    assert len(result["age_gap_flags"]) >= 1
    flag = result["age_gap_flags"][0]
    assert flag["age_gap"] >= 7  # 15-7 = 8 (or close depending on date)


@pytest.mark.asyncio
async def test_no_flag_for_small_age_gap(test_session: AsyncSession, graph_data):
    """No flag when age gap is within threshold (13yo contacts 10yo = 3yr gap)."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_13"].id,
        target_id=graph_data["child_10"].id,
        edge_type="contact",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_graph_analysis(test_session, graph_data["child_13"].id)
    # Gap of ~3 years should NOT be flagged (threshold is 4)
    flagged_ids = [f["contact_member_id"] for f in result["age_gap_flags"]]
    assert str(graph_data["child_10"].id) not in flagged_ids


@pytest.mark.asyncio
async def test_age_gap_severity_critical(test_session: AsyncSession, graph_data):
    """Critical severity for age gap >= 8."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_15"].id,
        target_id=graph_data["child_7"].id,
        edge_type="follow",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_graph_analysis(test_session, graph_data["child_15"].id)
    critical_flags = [f for f in result["age_gap_flags"] if f["severity"] == "critical"]
    assert len(critical_flags) >= 1


@pytest.mark.asyncio
async def test_analyze_nonexistent_member(test_session: AsyncSession):
    """Graph analysis for nonexistent member returns empty result."""
    result = await run_graph_analysis(test_session, uuid.uuid4())
    assert result["flagged_count"] == 0
    assert result["total_contacts"] == 0


# ---------------------------------------------------------------------------
# Isolation Detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_isolation_no_contacts(test_session: AsyncSession, graph_data):
    """Score socially isolated child with no contacts."""
    result = await run_isolation_check(test_session, graph_data["child_7"].id)
    assert result["isolation_score"] >= 50
    assert result["contact_count"] == 0
    has_no_contacts = any(i["indicator"] == "no_contacts" for i in result["indicators"])
    assert has_no_contacts


@pytest.mark.asyncio
async def test_detect_isolation_single_contact(test_session: AsyncSession, graph_data):
    """Single contact triggers single_contact indicator."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_7"].id,
        target_id=graph_data["child_8"].id,
        edge_type="contact",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_isolation_check(test_session, graph_data["child_7"].id)
    assert result["contact_count"] >= 1
    has_single = any(i["indicator"] == "single_contact" for i in result["indicators"])
    assert has_single


@pytest.mark.asyncio
async def test_detect_isolation_no_interactions(test_session: AsyncSession, graph_data):
    """Contacts without interactions triggers no_interactions indicator."""
    for target_key in ["child_8", "child_10", "child_13"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data["child_7"].id,
            target_id=graph_data[target_key].id,
            edge_type="contact",
            weight=1.0,
            last_interaction=None,
        )
        test_session.add(edge)
    await test_session.flush()

    result = await run_isolation_check(test_session, graph_data["child_7"].id)
    assert result["interaction_count"] == 0
    has_no_interaction = any(i["indicator"] == "no_interactions" for i in result["indicators"])
    assert has_no_interaction


@pytest.mark.asyncio
async def test_detect_isolation_healthy_member(test_session: AsyncSession, graph_data):
    """Well-connected member has low isolation score."""
    for target_key in ["child_8", "child_10", "child_13", "child_15"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data["child_7"].id,
            target_id=graph_data[target_key].id,
            edge_type="contact",
            weight=1.0,
            last_interaction=datetime(2026, 3, 20, 10, 0, 0, tzinfo=timezone.utc),
        )
        test_session.add(edge)
    # Also add incoming edges
    for src_key in ["child_8", "child_10"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data[src_key].id,
            target_id=graph_data["child_7"].id,
            edge_type="follow",
            weight=1.0,
            last_interaction=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
        )
        test_session.add(edge)
    await test_session.flush()

    result = await run_isolation_check(test_session, graph_data["child_7"].id)
    assert result["isolation_score"] < 30
    assert result["contact_count"] >= 4


@pytest.mark.asyncio
async def test_detect_isolation_one_directional(test_session: AsyncSession, graph_data):
    """Only outgoing edges triggers no_incoming indicator."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_7"].id,
        target_id=graph_data["child_8"].id,
        edge_type="follow",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_isolation_check(test_session, graph_data["child_7"].id)
    has_no_incoming = any(i["indicator"] == "no_incoming" for i in result["indicators"])
    assert has_no_incoming


# ---------------------------------------------------------------------------
# Influence Mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_influence_mapping_basic(test_session: AsyncSession, graph_data):
    """Map influence from incoming edges."""
    # child_15 influences child_7 via message and follow
    for etype in ["message", "follow"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data["child_15"].id,
            target_id=graph_data["child_7"].id,
            edge_type=etype,
            weight=1.0,
        )
        test_session.add(edge)
    await test_session.flush()

    result = await run_influence_mapping(test_session, graph_data["child_7"].id)
    assert len(result["influencers"]) >= 1
    assert result["influence_score"] > 0


@pytest.mark.asyncio
async def test_influence_mapping_message_weight(test_session: AsyncSession, graph_data):
    """Messages have higher influence weight than follows."""
    # Only a message edge
    edge_msg = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_13"].id,
        target_id=graph_data["child_7"].id,
        edge_type="message",
        weight=1.0,
    )
    # Only a follow edge from a different person
    edge_follow = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_10"].id,
        target_id=graph_data["child_7"].id,
        edge_type="follow",
        weight=1.0,
    )
    test_session.add(edge_msg)
    test_session.add(edge_follow)
    await test_session.flush()

    result = await run_influence_mapping(test_session, graph_data["child_7"].id)
    influencers = result["influencers"]
    assert len(influencers) == 2
    # Message sender should be ranked higher
    assert influencers[0]["member_id"] == str(graph_data["child_13"].id)


@pytest.mark.asyncio
async def test_influence_mapping_no_incoming(test_session: AsyncSession, graph_data):
    """Member with no incoming edges has zero influence score."""
    result = await run_influence_mapping(test_session, graph_data["child_7"].id)
    assert result["influence_score"] == 0.0
    assert len(result["influencers"]) == 0


@pytest.mark.asyncio
async def test_influence_mapping_multiple_edge_types(test_session: AsyncSession, graph_data):
    """Influencer with multiple edge types appears once with all types listed."""
    for etype in ["message", "follow", "mention"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data["child_15"].id,
            target_id=graph_data["child_7"].id,
            edge_type=etype,
            weight=1.0,
        )
        test_session.add(edge)
    await test_session.flush()

    result = await run_influence_mapping(test_session, graph_data["child_7"].id)
    assert len(result["influencers"]) == 1
    assert result["influencers"][0]["edge_count"] == 3
    assert set(result["influencers"][0]["edge_types"]) == {"message", "follow", "mention"}


# ---------------------------------------------------------------------------
# Abuse Signal Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_abuse_signal(test_session: AsyncSession, graph_data):
    """Create an abuse signal."""
    data = AbuseSignalCreate(
        member_id=graph_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
        details={"contact_id": str(graph_data["child_15"].id), "gap": 8},
    )
    signal = await create_abuse_signal(test_session, data)
    assert signal.id is not None
    assert signal.signal_type == "age_gap"
    assert signal.severity == "high"
    assert signal.resolved is False


@pytest.mark.asyncio
async def test_get_abuse_signals(test_session: AsyncSession, graph_data):
    """Get abuse signals for a member."""
    for stype in ["age_gap", "isolation"]:
        data = AbuseSignalCreate(
            member_id=graph_data["child_7"].id,
            signal_type=stype,
            severity="medium",
        )
        await create_abuse_signal(test_session, data)

    items, total = await get_abuse_signals(test_session, graph_data["child_7"].id)
    assert total == 2
    assert len(items) == 2


@pytest.mark.asyncio
async def test_get_abuse_signals_exclude_resolved(test_session: AsyncSession, graph_data):
    """Resolved signals excluded by default."""
    data = AbuseSignalCreate(
        member_id=graph_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
    )
    signal = await create_abuse_signal(test_session, data)
    await resolve_abuse_signal(test_session, signal.id, graph_data["user"].id)

    items, total = await get_abuse_signals(test_session, graph_data["child_7"].id)
    assert total == 0


@pytest.mark.asyncio
async def test_get_abuse_signals_include_resolved(test_session: AsyncSession, graph_data):
    """Include resolved signals when requested."""
    data = AbuseSignalCreate(
        member_id=graph_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
    )
    signal = await create_abuse_signal(test_session, data)
    await resolve_abuse_signal(test_session, signal.id, graph_data["user"].id)

    items, total = await get_abuse_signals(
        test_session, graph_data["child_7"].id, include_resolved=True,
    )
    assert total == 1


@pytest.mark.asyncio
async def test_resolve_abuse_signal(test_session: AsyncSession, graph_data):
    """Resolve an abuse signal."""
    data = AbuseSignalCreate(
        member_id=graph_data["child_7"].id,
        signal_type="isolation",
        severity="medium",
    )
    signal = await create_abuse_signal(test_session, data)
    resolved = await resolve_abuse_signal(test_session, signal.id, graph_data["user"].id)
    assert resolved.resolved is True
    assert resolved.resolved_at is not None
    assert resolved.resolved_by == graph_data["user"].id


@pytest.mark.asyncio
async def test_resolve_nonexistent_signal(test_session: AsyncSession):
    """Resolving nonexistent signal raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await resolve_abuse_signal(test_session, uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# Behavioral Baseline Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_baseline(test_session: AsyncSession, graph_data):
    """Create a behavioral baseline."""
    baseline = await create_baseline(
        test_session,
        member_id=graph_data["child_7"].id,
        window_days=30,
        metrics={"avg_contacts": 3, "avg_messages": 10},
        sample_count=30,
    )
    assert baseline.id is not None
    assert baseline.window_days == 30
    assert baseline.sample_count == 30


@pytest.mark.asyncio
async def test_get_baseline(test_session: AsyncSession, graph_data):
    """Get latest behavioral baseline."""
    await create_baseline(
        test_session,
        member_id=graph_data["child_7"].id,
        window_days=30,
        metrics={"avg_contacts": 3},
        sample_count=20,
    )
    result = await get_baseline(test_session, graph_data["child_7"].id, window_days=30)
    assert result is not None
    assert result.metrics == {"avg_contacts": 3}


@pytest.mark.asyncio
async def test_get_baseline_none(test_session: AsyncSession, graph_data):
    """Get baseline for member with none returns None."""
    result = await get_baseline(test_session, graph_data["child_7"].id, window_days=30)
    assert result is None


# ---------------------------------------------------------------------------
# Age-Inappropriate Pattern Detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_pattern_teen_contacts_young(test_session: AsyncSession, graph_data):
    """Detect teen with multiple young contacts as concerning pattern."""
    for target_key in ["child_7", "child_8"]:
        edge = SocialGraphEdge(
            id=uuid.uuid4(),
            source_id=graph_data["child_15"].id,
            target_id=graph_data[target_key].id,
            edge_type="contact",
            weight=1.0,
        )
        test_session.add(edge)
    await test_session.flush()

    result = await run_age_pattern_check(test_session, graph_data["child_15"].id)
    assert result["flagged"] is True
    assert any(s["pattern"] == "teen_contacts_young" for s in result["signals"])


@pytest.mark.asyncio
async def test_age_pattern_normal(test_session: AsyncSession, graph_data):
    """Normal same-tier contacts not flagged."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=graph_data["child_7"].id,
        target_id=graph_data["child_8"].id,
        edge_type="contact",
        weight=1.0,
    )
    test_session.add(edge)
    await test_session.flush()

    result = await run_age_pattern_check(test_session, graph_data["child_7"].id)
    assert result["flagged"] is False


@pytest.mark.asyncio
async def test_age_pattern_nonexistent_member(test_session: AsyncSession):
    """Age pattern check on nonexistent member returns unflagged."""
    result = await run_age_pattern_check(test_session, uuid.uuid4())
    assert result["flagged"] is False
    assert result["signals"] == []
