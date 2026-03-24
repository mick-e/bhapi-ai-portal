"""Correlation Rules Engine — pattern matching across event types to generate enriched alerts."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.intelligence.models import CorrelationRule, EnrichedAlert

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Rule Management
# ---------------------------------------------------------------------------


async def get_rules(
    db: AsyncSession,
    age_tier: str | None = None,
    enabled_only: bool = True,
) -> list[CorrelationRule]:
    """List correlation rules, optionally filtered by age tier."""
    q = select(CorrelationRule)

    if enabled_only:
        q = q.where(CorrelationRule.enabled.is_(True))

    if age_tier is not None:
        # Return rules that match the tier OR rules with null tier (all tiers)
        q = q.where(
            (CorrelationRule.age_tier_filter == age_tier)
            | (CorrelationRule.age_tier_filter.is_(None))
        )

    q = q.order_by(CorrelationRule.created_at.asc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_rule(db: AsyncSession, data: dict) -> CorrelationRule:
    """Create a correlation rule."""
    _validate_condition(data.get("condition", {}))

    rule = CorrelationRule(
        id=uuid4(),
        name=data["name"],
        description=data.get("description"),
        condition=data["condition"],
        action_severity=data.get("action_severity", "medium"),
        notification_type=data.get("notification_type", "alert"),
        age_tier_filter=data.get("age_tier_filter"),
        enabled=data.get("enabled", True),
    )
    db.add(rule)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(f"Correlation rule with name '{data['name']}' already exists")
    await db.refresh(rule)

    logger.info(
        "correlation_rule_created",
        rule_id=str(rule.id),
        name=rule.name,
        action_severity=rule.action_severity,
    )
    return rule


async def update_rule(
    db: AsyncSession,
    rule_id: UUID,
    data: dict,
) -> CorrelationRule:
    """Update an existing correlation rule."""
    result = await db.execute(
        select(CorrelationRule).where(CorrelationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundError("CorrelationRule")

    if "condition" in data:
        _validate_condition(data["condition"])
        rule.condition = data["condition"]

    allowed_fields = {
        "name", "description", "action_severity",
        "notification_type", "age_tier_filter", "enabled",
    }
    for field in allowed_fields:
        if field in data:
            setattr(rule, field, data[field])

    await db.flush()
    await db.refresh(rule)

    logger.info("correlation_rule_updated", rule_id=str(rule_id))
    return rule


# ---------------------------------------------------------------------------
# Event Evaluation
# ---------------------------------------------------------------------------


async def evaluate_event(db: AsyncSession, event: dict) -> list[dict]:
    """Match an incoming event against active rules within the 48h window.

    Returns a list of match dicts: {rule, signals, score, confidence}.
    """
    now = datetime.now(timezone.utc)
    age_tier = event.get("age_tier")

    rules = await get_rules(db, age_tier=age_tier, enabled_only=True)

    matches = []
    for rule in rules:
        condition = rule.condition or {}
        window_hours = condition.get("time_window_hours", 48)
        window_start = now - timedelta(hours=window_hours)

        # Enforce the window — skip if event is outside rule's window
        event_time = event.get("timestamp")
        if event_time is not None:
            if isinstance(event_time, str):
                try:
                    event_time = datetime.fromisoformat(event_time)
                except ValueError:
                    event_time = None
            if event_time is not None:
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                if event_time < window_start:
                    continue

        signals = condition.get("signals", [])
        logic = condition.get("logic", "AND").upper()

        matched_signals, total_score = _evaluate_signals(event, signals, logic)

        if matched_signals:
            confidence = _compute_confidence(matched_signals, signals, logic)
            matches.append({
                "rule": rule,
                "signals": matched_signals,
                "score": total_score,
                "confidence": confidence,
            })

    return matches


def _evaluate_signals(
    event: dict,
    signals: list[dict],
    logic: str,
) -> tuple[list[dict], float]:
    """Evaluate signal conditions against the event payload.

    Returns (matched_signals, aggregate_score).
    For AND: all signals must match.
    For OR: at least one signal must match.
    """
    event_metrics = event.get("metrics", {})
    matched = []
    total_score = 0.0

    for signal in signals:
        source = signal.get("source", "")
        metric = signal.get("metric", "")
        operator = signal.get("operator", "gt")
        threshold_multiplier = signal.get("threshold_multiplier", 1.0)

        # Check source matches — skip signals from a different source
        event_source = event.get("source", event.get("type", ""))
        if source and event_source and source != event_source:
            if logic == "AND":
                return [], 0.0
            continue

        value = event_metrics.get(metric)
        if value is None:
            value = event.get(metric)

        if value is None:
            if logic == "AND":
                return [], 0.0
            continue

        # Evaluate operator
        match_val = _apply_operator(value, operator, threshold_multiplier)
        if match_val:
            score = abs(value * threshold_multiplier) if isinstance(value, (int, float)) else 1.0
            matched.append({
                "source": source,
                "metric": metric,
                "value": value,
                "operator": operator,
                "threshold_multiplier": threshold_multiplier,
                "score_contribution": score,
            })
            total_score += score
        elif logic == "AND":
            return [], 0.0

    if logic == "OR" and not matched:
        return [], 0.0

    return matched, total_score


def _apply_operator(value, operator: str, threshold: float) -> bool:
    """Apply a comparison operator."""
    if not isinstance(value, (int, float)):
        return False
    ops = {
        "gt": value > threshold,
        "gte": value >= threshold,
        "lt": value < threshold,
        "lte": value <= threshold,
        "eq": value == threshold,
    }
    return ops.get(operator, False)


def _compute_confidence(matched: list[dict], all_signals: list[dict], logic: str) -> str:
    """Compute confidence level based on how many signals matched."""
    if not all_signals:
        return "low"
    ratio = len(matched) / max(len(all_signals), 1)
    if logic == "AND" or ratio >= 1.0:
        return "high"
    if ratio >= 0.6:
        return "medium"
    return "low"


def _validate_condition(condition: dict) -> None:
    """Validate condition structure to prevent injection."""
    if not isinstance(condition, dict):
        raise ValidationError("condition must be a JSON object")

    signals = condition.get("signals", [])
    if not isinstance(signals, list):
        raise ValidationError("condition.signals must be a list")

    valid_operators = {"gt", "gte", "lt", "lte", "eq"}
    valid_logic = {"AND", "OR"}

    logic = condition.get("logic", "AND")
    if logic not in valid_logic:
        raise ValidationError(f"condition.logic must be one of {valid_logic}")

    for sig in signals:
        if not isinstance(sig, dict):
            raise ValidationError("Each signal must be a JSON object")
        op = sig.get("operator", "gt")
        if op not in valid_operators:
            raise ValidationError(f"Signal operator must be one of {valid_operators}")
        tm = sig.get("threshold_multiplier", 1.0)
        if not isinstance(tm, (int, float)):
            raise ValidationError("threshold_multiplier must be numeric")


# ---------------------------------------------------------------------------
# Enriched Alerts
# ---------------------------------------------------------------------------


async def create_enriched_alert(
    db: AsyncSession,
    alert_id: UUID,
    rule_id: UUID | None,
    context: str,
    signals: dict,
    score: float,
    confidence: str,
) -> EnrichedAlert:
    """Create an enriched alert with correlation context."""
    enriched = EnrichedAlert(
        id=uuid4(),
        alert_id=alert_id,
        correlation_rule_id=rule_id,
        correlation_context=context,
        contributing_signals=signals,
        unified_risk_score=score,
        confidence=confidence,
    )
    db.add(enriched)
    await db.flush()
    await db.refresh(enriched)

    logger.info(
        "enriched_alert_created",
        enriched_id=str(enriched.id),
        alert_id=str(alert_id),
        rule_id=str(rule_id) if rule_id else None,
        score=score,
        confidence=confidence,
    )
    return enriched


async def get_enriched_alert(
    db: AsyncSession,
    alert_id: UUID,
) -> EnrichedAlert | None:
    """Get the enrichment record for an alert."""
    result = await db.execute(
        select(EnrichedAlert).where(EnrichedAlert.alert_id == alert_id)
    )
    return result.scalar_one_or_none()


async def get_enriched_alert_by_id(
    db: AsyncSession,
    enriched_alert_id: UUID,
) -> EnrichedAlert | None:
    """Get an enriched alert by its own primary key."""
    result = await db.execute(
        select(EnrichedAlert).where(EnrichedAlert.id == enriched_alert_id)
    )
    return result.scalar_one_or_none()
