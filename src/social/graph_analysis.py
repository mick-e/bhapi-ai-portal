"""Social graph analysis — age-inappropriate contacts, isolation, influence mapping."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.groups import GroupMember
from src.intelligence import AbuseSignal, SocialGraphEdge

logger = structlog.get_logger()

# Thresholds
AGE_GAP_THRESHOLD = 4  # years — flag if contacts differ by more than this
ISOLATION_HIGH_THRESHOLD = 70  # score above this = high isolation
INFLUENCE_WEIGHT_MULTIPLIER = {
    "contact": 1.0,
    "follow": 0.5,
    "message": 2.0,
    "mention": 0.3,
}


def _calculate_age(dob: datetime | None) -> int | None:
    """Calculate age from date of birth."""
    if dob is None:
        return None
    today = datetime.now(timezone.utc)
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


async def analyze_contacts(db: AsyncSession, member_id: UUID) -> dict:
    """Analyze contacts for age-inappropriate patterns.

    Returns: {age_gap_flags: [...], total_contacts: int, flagged_count: int}
    """
    # Get the member's date of birth
    member_result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        return {"age_gap_flags": [], "total_contacts": 0, "flagged_count": 0}

    member_age = _calculate_age(member.date_of_birth)
    if member_age is None:
        return {"age_gap_flags": [], "total_contacts": 0, "flagged_count": 0}

    # Get all edges where this member is source or target
    edges_result = await db.execute(
        select(SocialGraphEdge).where(
            (SocialGraphEdge.source_id == member_id)
            | (SocialGraphEdge.target_id == member_id)
        )
    )
    edges = list(edges_result.scalars().all())

    # Collect unique contact IDs
    contact_ids = set()
    for edge in edges:
        other_id = edge.target_id if edge.source_id == member_id else edge.source_id
        contact_ids.add(other_id)

    if not contact_ids:
        return {"age_gap_flags": [], "total_contacts": 0, "flagged_count": 0}

    # Get contact members' dates of birth
    contacts_result = await db.execute(
        select(GroupMember).where(GroupMember.id.in_(list(contact_ids)))
    )
    contacts = {c.id: c for c in contacts_result.scalars().all()}

    age_gap_flags = []
    for edge in edges:
        other_id = edge.target_id if edge.source_id == member_id else edge.source_id
        contact = contacts.get(other_id)
        if not contact:
            continue

        contact_age = _calculate_age(contact.date_of_birth)
        if contact_age is None:
            continue

        gap = abs(member_age - contact_age)
        if gap > AGE_GAP_THRESHOLD:
            severity = "critical" if gap >= 8 else "high" if gap >= 6 else "medium"
            age_gap_flags.append({
                "contact_member_id": str(other_id),
                "source_age": member_age,
                "target_age": contact_age,
                "age_gap": gap,
                "edge_type": edge.edge_type,
                "severity": severity,
            })

    logger.info(
        "graph_analysis_contacts",
        member_id=str(member_id),
        total_contacts=len(contact_ids),
        flagged=len(age_gap_flags),
    )

    return {
        "age_gap_flags": age_gap_flags,
        "total_contacts": len(contact_ids),
        "flagged_count": len(age_gap_flags),
    }


async def detect_isolation(db: AsyncSession, member_id: UUID) -> dict:
    """Detect social isolation for a member.

    Returns: {isolation_score: 0-100, indicators: [...], contact_count, interaction_count}
    """
    # Count edges (contacts)
    contact_count_result = await db.execute(
        select(func.count()).select_from(SocialGraphEdge).where(
            (SocialGraphEdge.source_id == member_id)
            | (SocialGraphEdge.target_id == member_id)
        )
    )
    contact_count = contact_count_result.scalar() or 0

    # Count recent interactions (edges with last_interaction set)
    interaction_result = await db.execute(
        select(func.count()).select_from(SocialGraphEdge).where(
            ((SocialGraphEdge.source_id == member_id)
             | (SocialGraphEdge.target_id == member_id)),
            SocialGraphEdge.last_interaction.isnot(None),
        )
    )
    interaction_count = interaction_result.scalar() or 0

    # Calculate isolation score (higher = more isolated)
    indicators = []
    score = 0.0

    if contact_count == 0:
        score += 50.0
        indicators.append({
            "indicator": "no_contacts",
            "description": "Member has no social connections",
            "weight": 50.0,
        })
    elif contact_count == 1:
        score += 25.0
        indicators.append({
            "indicator": "single_contact",
            "description": "Member has only one social connection",
            "weight": 25.0,
        })
    elif contact_count <= 2:
        score += 15.0
        indicators.append({
            "indicator": "few_contacts",
            "description": "Member has very few social connections",
            "weight": 15.0,
        })

    if interaction_count == 0 and contact_count > 0:
        score += 30.0
        indicators.append({
            "indicator": "no_interactions",
            "description": "Member has contacts but no recent interactions",
            "weight": 30.0,
        })
    elif contact_count > 0 and interaction_count < contact_count * 0.3:
        score += 15.0
        indicators.append({
            "indicator": "low_interaction_rate",
            "description": "Member interacts with less than 30% of contacts",
            "weight": 15.0,
        })

    # Check for one-directional relationships
    outgoing_result = await db.execute(
        select(func.count()).select_from(SocialGraphEdge).where(
            SocialGraphEdge.source_id == member_id,
        )
    )
    outgoing = outgoing_result.scalar() or 0

    incoming_result = await db.execute(
        select(func.count()).select_from(SocialGraphEdge).where(
            SocialGraphEdge.target_id == member_id,
        )
    )
    incoming = incoming_result.scalar() or 0

    if outgoing > 0 and incoming == 0:
        score += 20.0
        indicators.append({
            "indicator": "no_incoming",
            "description": "Member reaches out but receives no connections",
            "weight": 20.0,
        })

    # Cap at 100
    score = min(score, 100.0)

    logger.info(
        "graph_analysis_isolation",
        member_id=str(member_id),
        isolation_score=score,
        contact_count=contact_count,
        interaction_count=interaction_count,
    )

    return {
        "isolation_score": score,
        "indicators": indicators,
        "contact_count": contact_count,
        "interaction_count": interaction_count,
    }


async def map_influence(db: AsyncSession, member_id: UUID) -> dict:
    """Map influence patterns in a member's social graph.

    Returns: {influencers: [...], influence_score: float, total_connections: int}
    """
    # Get all edges where this member is the target (incoming influence)
    edges_result = await db.execute(
        select(SocialGraphEdge).where(
            SocialGraphEdge.target_id == member_id,
        )
    )
    incoming_edges = list(edges_result.scalars().all())

    # Get all edges where this member is the source (outgoing)
    outgoing_result = await db.execute(
        select(SocialGraphEdge).where(
            SocialGraphEdge.source_id == member_id,
        )
    )
    outgoing_edges = list(outgoing_result.scalars().all())

    total_connections = len(set(
        [e.source_id for e in incoming_edges] +
        [e.target_id for e in outgoing_edges]
    ))

    # Aggregate influence by source
    influencer_map: dict[UUID, dict] = {}
    for edge in incoming_edges:
        sid = edge.source_id
        if sid not in influencer_map:
            influencer_map[sid] = {
                "member_id": str(sid),
                "influence_score": 0.0,
                "edge_count": 0,
                "edge_types": [],
            }
        multiplier = INFLUENCE_WEIGHT_MULTIPLIER.get(edge.edge_type, 1.0)
        influencer_map[sid]["influence_score"] += edge.weight * multiplier
        influencer_map[sid]["edge_count"] += 1
        if edge.edge_type not in influencer_map[sid]["edge_types"]:
            influencer_map[sid]["edge_types"].append(edge.edge_type)

    # Sort by influence score descending
    influencers = sorted(
        influencer_map.values(),
        key=lambda x: x["influence_score"],
        reverse=True,
    )

    # Overall influence score: sum of all incoming influence
    total_influence = sum(i["influence_score"] for i in influencers)

    logger.info(
        "graph_analysis_influence",
        member_id=str(member_id),
        influencer_count=len(influencers),
        total_influence=total_influence,
        total_connections=total_connections,
    )

    return {
        "influencers": influencers,
        "influence_score": total_influence,
        "total_connections": total_connections,
    }


async def detect_age_inappropriate_pattern(db: AsyncSession, member_id: UUID) -> dict:
    """Detect concerning age-tier mismatches in the member's social graph.

    Flags patterns where a member in one age tier has disproportionate contacts
    in significantly different tiers. For example, a teen (13-15) with many
    contacts in the young (5-9) tier.

    Returns: {flagged: bool, tier_distribution: {...}, signals: [...]}
    """
    # Get the member
    member_result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        return {"flagged": False, "tier_distribution": {}, "signals": []}

    member_age = _calculate_age(member.date_of_birth)
    if member_age is None:
        return {"flagged": False, "tier_distribution": {}, "signals": []}

    member_tier = _age_to_tier(member_age)

    # Get all contacts
    edges_result = await db.execute(
        select(SocialGraphEdge).where(
            (SocialGraphEdge.source_id == member_id)
            | (SocialGraphEdge.target_id == member_id)
        )
    )
    edges = list(edges_result.scalars().all())

    contact_ids = set()
    for edge in edges:
        other_id = edge.target_id if edge.source_id == member_id else edge.source_id
        contact_ids.add(other_id)

    if not contact_ids:
        return {"flagged": False, "tier_distribution": {}, "signals": []}

    contacts_result = await db.execute(
        select(GroupMember).where(GroupMember.id.in_(list(contact_ids)))
    )
    contacts = list(contacts_result.scalars().all())

    # Count contacts by tier
    tier_distribution: dict[str, int] = {"young": 0, "preteen": 0, "teen": 0, "unknown": 0}
    for contact in contacts:
        contact_age = _calculate_age(contact.date_of_birth)
        if contact_age is None:
            tier_distribution["unknown"] += 1
        else:
            tier = _age_to_tier(contact_age)
            tier_distribution[tier] += 1

    # Detect concerning patterns
    signals = []
    flagged = False

    # A teen contacting many young children
    if member_tier == "teen" and tier_distribution.get("young", 0) >= 2:
        flagged = True
        signals.append({
            "pattern": "teen_contacts_young",
            "description": f"Teen member has {tier_distribution['young']} contacts in the young (5-9) tier",
            "severity": "high",
        })

    # A preteen with many young children contacts
    if member_tier == "preteen" and tier_distribution.get("young", 0) >= 3:
        flagged = True
        signals.append({
            "pattern": "preteen_many_young_contacts",
            "description": f"Preteen member has {tier_distribution['young']} contacts in the young (5-9) tier",
            "severity": "medium",
        })

    # Any member with contacts across all tiers (unusual pattern)
    tiers_with_contacts = sum(1 for t in ["young", "preteen", "teen"] if tier_distribution.get(t, 0) > 0)
    if tiers_with_contacts == 3 and len(contact_ids) >= 5:
        signals.append({
            "pattern": "cross_tier_spread",
            "description": "Member has contacts across all age tiers",
            "severity": "low",
        })

    if signals:
        # Create abuse signals for flagged patterns
        for signal in signals:
            if signal["severity"] in ("high", "critical"):
                abuse_signal = AbuseSignal(
                    member_id=member_id,
                    signal_type="age_gap",
                    severity=signal["severity"],
                    details=signal,
                    resolved=False,
                )
                db.add(abuse_signal)

    logger.info(
        "graph_analysis_age_pattern",
        member_id=str(member_id),
        member_tier=member_tier,
        flagged=flagged,
        signal_count=len(signals),
    )

    return {
        "flagged": flagged,
        "tier_distribution": tier_distribution,
        "signals": signals,
    }


def _age_to_tier(age: int) -> str:
    """Convert age to tier name."""
    if age <= 9:
        return "young"
    elif age <= 12:
        return "preteen"
    elif age <= 15:
        return "teen"
    return "teen"  # 16+ treated as teen for this analysis
