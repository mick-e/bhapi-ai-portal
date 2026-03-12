"""Portal BFF service — aggregates data from other modules."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.billing.models import BudgetThreshold, LLMAccount, SpendRecord
from src.capture.models import CaptureEvent
from src.groups.models import Group, GroupMember
from src.portal.schemas import (
    ActivityFeedItem,
    AlertSummary,
    CategoryCount,
    DashboardAlertItem,
    DashboardResponse,
    GroupSettingsResponse,
    NotificationPreferences,
    RiskSummary,
    SpendSummary,
    TrendDataPoint,
    UpdateGroupSettingsRequest,
)
from src.risk.models import RiskEvent

logger = structlog.get_logger()


async def get_dashboard(db: AsyncSession, group_id: UUID, user_id: UUID) -> DashboardResponse:
    """Aggregate dashboard data for a group (FR-010).

    Each section is wrapped in try/except so a single query failure
    (e.g. missing migration column) does not crash the entire dashboard.
    """
    # Get group
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        from src.exceptions import NotFoundError
        raise NotFoundError("Group", str(group_id))

    # Time boundaries
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Members ---
    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())
    total_members = len(members)
    member_names = {m.id: m.display_name for m in members}

    # --- Active members & interactions ---
    active_members = 0
    interactions_today = 0
    interactions_trend = "tracking"
    recent_activity: list[ActivityFeedItem] = []
    try:
        active_result = await db.execute(
            select(func.count(func.distinct(CaptureEvent.member_id)))
            .where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.timestamp >= now - timedelta(hours=24),
            )
        )
        active_members = active_result.scalar() or 0

        interactions_result = await db.execute(
            select(func.count(CaptureEvent.id))
            .where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.timestamp >= today_start,
            )
        )
        interactions_today = interactions_result.scalar() or 0

        yesterday_result = await db.execute(
            select(func.count(CaptureEvent.id))
            .where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.timestamp >= yesterday_start,
                CaptureEvent.timestamp < today_start,
            )
        )
        yesterday_count = yesterday_result.scalar() or 0
        if yesterday_count > 0:
            change = ((interactions_today - yesterday_count) / yesterday_count) * 100
            interactions_trend = f"{change:+.0f}% vs yesterday"

        # Recent Activity (last 10 events)
        recent_events_result = await db.execute(
            select(CaptureEvent)
            .where(CaptureEvent.group_id == group_id)
            .order_by(CaptureEvent.timestamp.desc())
            .limit(10)
        )
        recent_events = list(recent_events_result.scalars().all())
        recent_activity = [
            ActivityFeedItem(
                id=e.id,
                group_id=e.group_id,
                member_id=e.member_id,
                member_name=member_names.get(e.member_id, "Unknown"),
                provider=e.platform,
                model="",
                event_type=e.event_type,
                risk_level="low",
                timestamp=e.timestamp.isoformat() if e.timestamp else "",
            )
            for e in recent_events
        ]
    except Exception:
        logger.exception("dashboard_activity_section_failed", group_id=str(group_id))

    # --- Alert Summary ---
    alert_summary = AlertSummary()
    try:
        unread_result = await db.execute(
            select(func.count(Alert.id))
            .where(
                Alert.group_id == group_id,
                Alert.status != "acknowledged",
            )
        )
        unread_count = unread_result.scalar() or 0

        critical_result = await db.execute(
            select(func.count(Alert.id))
            .where(
                Alert.group_id == group_id,
                Alert.status != "acknowledged",
                Alert.severity == "critical",
            )
        )
        critical_count = critical_result.scalar() or 0

        recent_alerts_result = await db.execute(
            select(Alert)
            .where(Alert.group_id == group_id)
            .order_by(Alert.created_at.desc())
            .limit(5)
        )
        recent_alerts = list(recent_alerts_result.scalars().all())

        severity_map = {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info",
            "info": "info",
        }

        recent_alert_items = [
            DashboardAlertItem(
                id=a.id,
                group_id=a.group_id,
                type="risk",
                severity=severity_map.get(a.severity, "info"),
                title=a.title,
                message=a.body,
                member_name=member_names.get(a.member_id, None) if a.member_id else None,
                read=a.status == "acknowledged",
                actioned=a.status == "acknowledged",
                related_member_id=a.member_id,
                related_event_id=a.risk_event_id,
                created_at=a.created_at.isoformat() if a.created_at else "",
            )
            for a in recent_alerts
        ]

        alert_summary = AlertSummary(
            unread_count=unread_count,
            critical_count=critical_count,
            recent=recent_alert_items,
        )
    except Exception:
        logger.exception("dashboard_alerts_section_failed", group_id=str(group_id))

    # --- Spend Summary ---
    spend_summary = SpendSummary()
    try:
        month_spend_result = await db.execute(
            select(func.coalesce(func.sum(SpendRecord.amount), 0.0))
            .where(
                SpendRecord.group_id == group_id,
                SpendRecord.period_start >= month_start,
            )
        )
        month_usd = float(month_spend_result.scalar() or 0.0)

        today_spend_result = await db.execute(
            select(func.coalesce(func.sum(SpendRecord.amount), 0.0))
            .where(
                SpendRecord.group_id == group_id,
                SpendRecord.period_start >= today_start,
            )
        )
        today_usd = float(today_spend_result.scalar() or 0.0)

        budget_result = await db.execute(
            select(BudgetThreshold.amount).where(
                BudgetThreshold.group_id == group_id,
                BudgetThreshold.member_id.is_(None),
            ).order_by(BudgetThreshold.created_at.desc()).limit(1)
        )
        budget_usd = float(budget_result.scalar() or 0.0)
        budget_pct = (month_usd / budget_usd * 100.0) if budget_usd > 0 else 0.0

        top_provider_name = ""
        top_provider_cost = 0.0
        top_provider_pct = 0.0
        if month_usd > 0:
            provider_spend_result = await db.execute(
                select(
                    LLMAccount.provider,
                    func.coalesce(func.sum(SpendRecord.amount), 0.0).label("total"),
                )
                .join(LLMAccount, SpendRecord.llm_account_id == LLMAccount.id)
                .where(
                    SpendRecord.group_id == group_id,
                    SpendRecord.period_start >= month_start,
                )
                .group_by(LLMAccount.provider)
                .order_by(func.sum(SpendRecord.amount).desc())
                .limit(1)
            )
            row = provider_spend_result.first()
            if row:
                top_provider_name = row[0] or ""
                top_provider_cost = float(row[1])
                top_provider_pct = (top_provider_cost / month_usd * 100.0) if month_usd > 0 else 0.0

        top_member_name = ""
        top_member_cost = 0.0
        top_member_pct = 0.0
        if month_usd > 0:
            member_spend_result = await db.execute(
                select(
                    SpendRecord.member_id,
                    func.coalesce(func.sum(SpendRecord.amount), 0.0).label("total"),
                )
                .where(
                    SpendRecord.group_id == group_id,
                    SpendRecord.period_start >= month_start,
                    SpendRecord.member_id.isnot(None),
                )
                .group_by(SpendRecord.member_id)
                .order_by(func.sum(SpendRecord.amount).desc())
                .limit(1)
            )
            mrow = member_spend_result.first()
            if mrow and mrow[0]:
                top_member_cost = float(mrow[1])
                top_member_pct = (top_member_cost / month_usd * 100.0) if month_usd > 0 else 0.0
                top_member_name = member_names.get(mrow[0], "Unknown")

        spend_summary = SpendSummary(
            today_usd=today_usd,
            month_usd=month_usd,
            budget_usd=budget_usd,
            budget_used_percentage=round(budget_pct, 1),
            top_provider=top_provider_name,
            top_provider_cost_usd=round(top_provider_cost, 2),
            top_provider_percentage=round(top_provider_pct, 1),
            top_member=top_member_name,
            top_member_cost_usd=round(top_member_cost, 2),
            top_member_percentage=round(top_member_pct, 1),
        )
    except Exception:
        logger.exception("dashboard_spend_section_failed", group_id=str(group_id))

    # --- Risk Summary ---
    risk_summary = RiskSummary()
    try:
        risk_today_result = await db.execute(
            select(func.count(RiskEvent.id))
            .where(
                RiskEvent.group_id == group_id,
                RiskEvent.created_at >= today_start,
            )
        )
        total_events_today = risk_today_result.scalar() or 0

        high_sev_result = await db.execute(
            select(func.count(RiskEvent.id))
            .where(
                RiskEvent.group_id == group_id,
                RiskEvent.created_at >= today_start,
                RiskEvent.severity.in_(["critical", "high"]),
            )
        )
        high_severity_count = high_sev_result.scalar() or 0

        yesterday_risk_result = await db.execute(
            select(func.count(RiskEvent.id))
            .where(
                RiskEvent.group_id == group_id,
                RiskEvent.created_at >= yesterday_start,
                RiskEvent.created_at < today_start,
            )
        )
        yesterday_risk = yesterday_risk_result.scalar() or 0

        if total_events_today > yesterday_risk:
            trend = "increasing"
        elif total_events_today < yesterday_risk:
            trend = "decreasing"
        else:
            trend = "stable"

        risk_summary = RiskSummary(
            total_events_today=total_events_today,
            high_severity_count=high_severity_count,
            trend=trend,
        )
    except Exception:
        logger.exception("dashboard_risk_section_failed", group_id=str(group_id))

    # --- Activity Trend (last 7 days) ---
    activity_trend: list[TrendDataPoint] = []
    try:
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_count_result = await db.execute(
                select(func.count(CaptureEvent.id)).where(
                    CaptureEvent.group_id == group_id,
                    CaptureEvent.timestamp >= day_start,
                    CaptureEvent.timestamp < day_end,
                )
            )
            activity_trend.append(TrendDataPoint(
                date=day_start.strftime("%Y-%m-%d"),
                count=day_count_result.scalar() or 0,
            ))
    except Exception:
        logger.exception("dashboard_activity_trend_failed", group_id=str(group_id))

    # --- Risk Breakdown (by category, last 30 days) ---
    risk_breakdown: list[CategoryCount] = []
    try:
        risk_cat_result = await db.execute(
            select(RiskEvent.category, func.count(RiskEvent.id))
            .where(
                RiskEvent.group_id == group_id,
                RiskEvent.created_at >= now - timedelta(days=30),
            )
            .group_by(RiskEvent.category)
            .order_by(func.count(RiskEvent.id).desc())
        )
        risk_breakdown = [
            CategoryCount(category=row[0], count=row[1])
            for row in risk_cat_result.all()
        ]
    except Exception:
        logger.exception("dashboard_risk_breakdown_failed", group_id=str(group_id))

    # --- Spend Trend (last 7 days) ---
    spend_trend: list[TrendDataPoint] = []
    try:
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_spend_result = await db.execute(
                select(func.coalesce(func.sum(SpendRecord.amount), 0.0)).where(
                    SpendRecord.group_id == group_id,
                    SpendRecord.period_start >= day_start,
                    SpendRecord.period_start < day_end,
                )
            )
            spend_trend.append(TrendDataPoint(
                date=day_start.strftime("%Y-%m-%d"),
                amount=round(float(day_spend_result.scalar() or 0.0), 2),
            ))
    except Exception:
        logger.exception("dashboard_spend_trend_failed", group_id=str(group_id))

    return DashboardResponse(
        active_members=active_members,
        total_members=total_members,
        interactions_today=interactions_today,
        interactions_trend=interactions_trend,
        recent_activity=recent_activity,
        alert_summary=alert_summary,
        spend_summary=spend_summary,
        risk_summary=risk_summary,
        activity_trend=activity_trend,
        risk_breakdown=risk_breakdown,
        spend_trend=spend_trend,
    )


async def get_group_settings(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupSettingsResponse:
    """Get group settings for the settings page."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        from src.exceptions import NotFoundError
        raise NotFoundError("Group", str(group_id))

    settings = group.settings or {}

    # Get budget from BudgetThreshold
    budget_result = await db.execute(
        select(BudgetThreshold.amount).where(
            BudgetThreshold.group_id == group_id,
            BudgetThreshold.member_id.is_(None),
        ).order_by(BudgetThreshold.created_at.desc()).limit(1)
    )
    budget = float(budget_result.scalar() or 0.0)

    # Map notification prefs from settings dict
    notif_data = settings.get("notifications", {})
    notifications = NotificationPreferences(
        critical_safety=notif_data.get("critical_safety", True),
        risk_warnings=notif_data.get("risk_warnings", True),
        spend_alerts=notif_data.get("spend_alerts", True),
        member_updates=notif_data.get("member_updates", True),
        weekly_digest=notif_data.get("weekly_digest", True),
        report_notifications=notif_data.get("report_notifications", True),
    )

    # Trial status
    from src.billing.trial import get_trial_status
    trial = await get_trial_status(db, group_id)

    return GroupSettingsResponse(
        group_id=group.id,
        group_name=group.name,
        account_type=group.type,
        safety_level=settings.get("safety_level", "strict"),
        auto_block_critical=settings.get("auto_block_critical", True),
        prompt_logging=settings.get("prompt_logging", True),
        pii_detection=settings.get("pii_detection", True),
        notifications=notifications,
        monthly_budget_usd=budget,
        plan=trial.plan,
        trial_active=trial.is_active,
        trial_days_remaining=trial.days_remaining,
        trial_end=trial.trial_end.isoformat() if trial.trial_end else None,
        trial_locked=trial.is_locked,
    )


async def update_group_settings(
    db: AsyncSession, group_id: UUID, user_id: UUID, data: UpdateGroupSettingsRequest
) -> GroupSettingsResponse:
    """Update group settings."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        from src.exceptions import NotFoundError
        raise NotFoundError("Group", str(group_id))

    # Verify admin access
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        from src.exceptions import ForbiddenError
        raise ForbiddenError("You are not a member of this group")

    admin_roles = {"parent", "school_admin", "club_admin"}
    if member.role not in admin_roles:
        from src.exceptions import ForbiddenError
        raise ForbiddenError("Admin role required")

    settings = dict(group.settings or {})

    if data.group_name is not None:
        group.name = data.group_name
    if data.safety_level is not None:
        settings["safety_level"] = data.safety_level
    if data.auto_block_critical is not None:
        settings["auto_block_critical"] = data.auto_block_critical
    if data.prompt_logging is not None:
        settings["prompt_logging"] = data.prompt_logging
    if data.pii_detection is not None:
        settings["pii_detection"] = data.pii_detection
    if data.notifications is not None:
        existing_notif = settings.get("notifications", {})
        existing_notif.update(data.notifications)
        settings["notifications"] = existing_notif

    group.settings = settings

    # Update budget if provided
    if data.monthly_budget_usd is not None:
        from uuid import uuid4 as _uuid4
        budget_result = await db.execute(
            select(BudgetThreshold).where(
                BudgetThreshold.group_id == group_id,
                BudgetThreshold.member_id.is_(None),
            ).order_by(BudgetThreshold.created_at.desc()).limit(1)
        )
        existing_budget = budget_result.scalar_one_or_none()
        if existing_budget:
            existing_budget.amount = data.monthly_budget_usd
        else:
            new_budget = BudgetThreshold(
                id=_uuid4(),
                group_id=group_id,
                member_id=None,
                amount=data.monthly_budget_usd,
                currency="USD",
                type="hard",
            )
            db.add(new_budget)

    await db.flush()
    await db.refresh(group)

    return await get_group_settings(db, group_id, user_id)
