"""Portal BFF service — aggregates data from other modules."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts import Alert
from src.billing import BudgetThreshold, LLMAccount, SpendRecord
from src.capture import CaptureEvent
from src.contacts import Contact
from src.groups import Group, GroupMember
from src.messaging import Message
from src.moderation import ModerationQueue
from src.portal.schemas import (
    ActivityFeedItem,
    AlertSummary,
    CategoryCount,
    ChildProfileResponse,
    DashboardAlertItem,
    DashboardResponse,
    FlaggedContentItem,
    GroupSettingsResponse,
    NotificationPreferences,
    PlatformBreakdown,
    RiskSummary,
    RiskTrendPoint,
    SocialActivityResponse,
    SpendSummary,
    TimelineItem,
    TimeTrendPoint,
    TrendDataPoint,
    UpdateGroupSettingsRequest,
)
from src.risk import RiskEvent
from src.schemas import GroupContext
from src.social import SocialPost

logger = structlog.get_logger()

# Time estimate: average minutes per social interaction (post or message)
_MINUTES_PER_POST = 5
_MINUTES_PER_MESSAGE = 2


async def get_dashboard(db: AsyncSession, group_id: UUID, user_id: UUID) -> DashboardResponse:
    """Aggregate dashboard data for a group (FR-010).

    Each section is wrapped in try/except so a single query failure
    (e.g. missing migration column) does not crash the entire dashboard.
    The degraded_sections list tracks which sections failed to load.
    """
    degraded_sections: list[str] = []

    # Get group — allow NotFoundError to propagate (404 is correct),
    # but catch DB errors to avoid 500s
    try:
        result = await db.execute(select(Group).where(Group.id == group_id))
        group = result.scalar_one_or_none()
        if not group:
            from src.exceptions import NotFoundError
            raise NotFoundError("Group", str(group_id))
    except Exception as exc:
        # Re-raise NotFoundError (legitimate 404)
        from src.exceptions import NotFoundError
        if isinstance(exc, NotFoundError):
            raise
        logger.exception("dashboard_group_lookup_failed", group_id=str(group_id))
        return DashboardResponse(degraded_sections=["all"])

    # Time boundaries
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Members ---
    members: list = []
    total_members = 0
    member_names: dict = {}
    try:
        members_result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        )
        members = list(members_result.scalars().all())
        total_members = len(members)
        member_names = {m.id: m.display_name for m in members}
    except Exception:
        logger.exception("dashboard_members_section_failed", group_id=str(group_id))
        degraded_sections.append("members")

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
        degraded_sections.append("activity")

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
        degraded_sections.append("alerts")

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
        degraded_sections.append("spend")

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
        degraded_sections.append("risk")

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
        degraded_sections.append("activity_trend")

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
        degraded_sections.append("risk_breakdown")

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
        degraded_sections.append("spend_trend")

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
        degraded_sections=degraded_sections,
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


async def get_social_activity(
    db: AsyncSession, member_id: UUID, auth: GroupContext,
) -> SocialActivityResponse:
    """Aggregate social activity for a child member (P2-M1).

    Only parents / school_admins / club_admins may call this.
    Each section is wrapped in try/except for partial-failure resilience.
    """
    from src.exceptions import ForbiddenError, NotFoundError

    # --- Verify caller has admin role ---
    admin_roles = {"parent", "school_admin", "club_admin"}
    if auth.role not in admin_roles:
        raise ForbiddenError("Parent or admin role required to view social activity")

    if not auth.group_id:
        from src.exceptions import ValidationError
        raise ValidationError("No group context")

    # --- Resolve the target member ---
    degraded_sections: list[str] = []

    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == auth.group_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    # The child must have a user_id to query social data
    child_user_id = member.user_id

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # --- Post counts ---
    post_count_7d = 0
    post_count_30d = 0
    try:
        if child_user_id:
            r7 = await db.execute(
                select(func.count(SocialPost.id)).where(
                    SocialPost.author_id == child_user_id,
                    SocialPost.created_at >= seven_days_ago,
                )
            )
            post_count_7d = r7.scalar() or 0

            r30 = await db.execute(
                select(func.count(SocialPost.id)).where(
                    SocialPost.author_id == child_user_id,
                    SocialPost.created_at >= thirty_days_ago,
                )
            )
            post_count_30d = r30.scalar() or 0
    except Exception:
        logger.exception("social_activity_posts_failed", member_id=str(member_id))
        degraded_sections.append("posts")

    # --- Message counts ---
    message_count_7d = 0
    message_count_30d = 0
    try:
        if child_user_id:
            m7 = await db.execute(
                select(func.count(Message.id)).where(
                    Message.sender_id == child_user_id,
                    Message.created_at >= seven_days_ago,
                )
            )
            message_count_7d = m7.scalar() or 0

            m30 = await db.execute(
                select(func.count(Message.id)).where(
                    Message.sender_id == child_user_id,
                    Message.created_at >= thirty_days_ago,
                )
            )
            message_count_30d = m30.scalar() or 0
    except Exception:
        logger.exception("social_activity_messages_failed", member_id=str(member_id))
        degraded_sections.append("messages")

    # --- Contacts ---
    contact_count = 0
    pending_contact_requests = 0
    try:
        if child_user_id:
            accepted = await db.execute(
                select(func.count(Contact.id)).where(
                    or_(
                        Contact.requester_id == child_user_id,
                        Contact.target_id == child_user_id,
                    ),
                    Contact.status == "accepted",
                )
            )
            contact_count = accepted.scalar() or 0

            pending = await db.execute(
                select(func.count(Contact.id)).where(
                    or_(
                        Contact.requester_id == child_user_id,
                        Contact.target_id == child_user_id,
                    ),
                    Contact.status == "pending",
                )
            )
            pending_contact_requests = pending.scalar() or 0
    except Exception:
        logger.exception("social_activity_contacts_failed", member_id=str(member_id))
        degraded_sections.append("contacts")

    # --- Flagged content ---
    flagged_content_count = 0
    flagged_items: list[FlaggedContentItem] = []
    try:
        if child_user_id:
            # Find flagged posts
            flagged_post_ids_result = await db.execute(
                select(SocialPost.id).where(
                    SocialPost.author_id == child_user_id,
                    SocialPost.moderation_status.in_(["rejected", "removed"]),
                )
            )
            flagged_post_ids = [r[0] for r in flagged_post_ids_result.all()]

            # Find moderation queue items for the child's content
            if flagged_post_ids:
                mod_result = await db.execute(
                    select(ModerationQueue).where(
                        ModerationQueue.content_id.in_(flagged_post_ids),
                        ModerationQueue.status.in_(["rejected", "escalated"]),
                    ).order_by(ModerationQueue.created_at.desc()).limit(10)
                )
                mod_items = list(mod_result.scalars().all())
                flagged_content_count = len(flagged_post_ids)
                flagged_items = [
                    FlaggedContentItem(
                        id=item.id,
                        content_type=item.content_type,
                        content_id=item.content_id,
                        status=item.status,
                        created_at=item.created_at.isoformat() if item.created_at else "",
                    )
                    for item in mod_items
                ]
            else:
                # Also check moderation queue directly for messages
                msg_mod_result = await db.execute(
                    select(func.count(ModerationQueue.id)).where(
                        ModerationQueue.content_type == "message",
                        ModerationQueue.status.in_(["rejected", "escalated"]),
                    )
                )
                flagged_content_count = msg_mod_result.scalar() or 0
    except Exception:
        logger.exception("social_activity_flagged_failed", member_id=str(member_id))
        degraded_sections.append("flagged")

    # --- Time estimates ---
    time_spent_minutes_7d = (post_count_7d * _MINUTES_PER_POST) + (message_count_7d * _MINUTES_PER_MESSAGE)
    time_spent_minutes_30d = (post_count_30d * _MINUTES_PER_POST) + (message_count_30d * _MINUTES_PER_MESSAGE)

    # --- Time trend (daily for last 7 days) ---
    time_trend: list[TimeTrendPoint] = []
    try:
        if child_user_id:
            for i in range(6, -1, -1):
                day_start = (now - timedelta(days=i)).replace(
                    hour=0, minute=0, second=0, microsecond=0,
                )
                day_end = day_start + timedelta(days=1)

                day_posts_r = await db.execute(
                    select(func.count(SocialPost.id)).where(
                        SocialPost.author_id == child_user_id,
                        SocialPost.created_at >= day_start,
                        SocialPost.created_at < day_end,
                    )
                )
                day_posts = day_posts_r.scalar() or 0

                day_msgs_r = await db.execute(
                    select(func.count(Message.id)).where(
                        Message.sender_id == child_user_id,
                        Message.created_at >= day_start,
                        Message.created_at < day_end,
                    )
                )
                day_msgs = day_msgs_r.scalar() or 0

                day_minutes = (day_posts * _MINUTES_PER_POST) + (day_msgs * _MINUTES_PER_MESSAGE)
                time_trend.append(TimeTrendPoint(
                    date=day_start.strftime("%Y-%m-%d"),
                    minutes=day_minutes,
                ))
    except Exception:
        logger.exception("social_activity_time_trend_failed", member_id=str(member_id))
        degraded_sections.append("time_trend")

    return SocialActivityResponse(
        member_id=member.id,
        member_name=member.display_name,
        post_count_7d=post_count_7d,
        post_count_30d=post_count_30d,
        message_count_7d=message_count_7d,
        message_count_30d=message_count_30d,
        contact_count=contact_count,
        pending_contact_requests=pending_contact_requests,
        flagged_content_count=flagged_content_count,
        flagged_items=flagged_items,
        time_spent_minutes_7d=time_spent_minutes_7d,
        time_spent_minutes_30d=time_spent_minutes_30d,
        time_trend=time_trend,
        degraded_sections=degraded_sections,
    )


async def get_child_profile(
    db: AsyncSession, member_id: UUID, auth: GroupContext,
) -> ChildProfileResponse:
    """Aggregate a combined child profile with AI + social timeline,
    risk trend, and platform breakdown (P2-M4).

    Only parents / school_admins / club_admins may call this.
    Each section is wrapped in try/except for partial-failure resilience.
    """
    from src.exceptions import ForbiddenError, NotFoundError, ValidationError

    admin_roles = {"parent", "school_admin", "club_admin"}
    if auth.role not in admin_roles:
        raise ForbiddenError("Parent or admin role required to view child profile")

    if not auth.group_id:
        raise ValidationError("No group context")

    degraded_sections: list[str] = []

    # --- Resolve target member ---
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == auth.group_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Member", str(member_id))

    child_user_id = member.user_id
    now = datetime.now(timezone.utc)
    now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # --- Avatar & age tier (from social profile if exists) ---
    avatar_url: str | None = None
    age_tier: str | None = None
    try:
        if child_user_id:
            from src.social.models import Profile
            prof_result = await db.execute(
                select(Profile).where(Profile.user_id == child_user_id)
            )
            profile = prof_result.scalar_one_or_none()
            if profile:
                avatar_url = profile.avatar_url
                age_tier = profile.age_tier
    except Exception:
        logger.exception("child_profile_avatar_failed", member_id=str(member_id))
        degraded_sections.append("profile")

    # --- Risk score (percentage of non-high events in last 30 days) ---
    risk_score = 0
    try:
        total_risk_30d_r = await db.execute(
            select(func.count(RiskEvent.id)).where(
                RiskEvent.member_id == member_id,
                RiskEvent.created_at >= thirty_days_ago,
            )
        )
        total_risk_30d = total_risk_30d_r.scalar() or 0

        high_risk_30d_r = await db.execute(
            select(func.count(RiskEvent.id)).where(
                RiskEvent.member_id == member_id,
                RiskEvent.created_at >= thirty_days_ago,
                RiskEvent.severity.in_(["critical", "high"]),
            )
        )
        high_risk_30d = high_risk_30d_r.scalar() or 0

        if total_risk_30d > 0:
            # Higher score = safer; 100 if no high/critical events
            risk_score = max(0, min(100, 100 - int(high_risk_30d / total_risk_30d * 100)))
        else:
            risk_score = 100  # no risk events = safest
    except Exception:
        logger.exception("child_profile_risk_score_failed", member_id=str(member_id))
        degraded_sections.append("risk_score")

    # --- Unified timeline (last 50 events across all sources) ---
    timeline: list[TimelineItem] = []
    try:
        # AI captures
        captures_r = await db.execute(
            select(CaptureEvent).where(
                CaptureEvent.member_id == member_id,
            ).order_by(CaptureEvent.timestamp.desc()).limit(20)
        )
        for ce in captures_r.scalars().all():
            timeline.append(TimelineItem(
                id=ce.id,
                source="ai",
                event_type=ce.event_type,
                title=f"AI {ce.event_type} on {ce.platform}",
                detail="",
                platform=ce.platform,
                timestamp=ce.timestamp.isoformat() if ce.timestamp else "",
            ))
    except Exception:
        logger.exception("child_profile_ai_timeline_failed", member_id=str(member_id))
        degraded_sections.append("ai_timeline")

    try:
        # Social posts
        if child_user_id:
            posts_r = await db.execute(
                select(SocialPost).where(
                    SocialPost.author_id == child_user_id,
                ).order_by(SocialPost.created_at.desc()).limit(15)
            )
            for sp in posts_r.scalars().all():
                timeline.append(TimelineItem(
                    id=sp.id,
                    source="social_post",
                    event_type="post",
                    title=f"Social post ({sp.post_type})",
                    detail=sp.content[:100] if sp.content else "",
                    platform="bhapi_social",
                    timestamp=sp.created_at.isoformat() if sp.created_at else "",
                ))
    except Exception:
        logger.exception("child_profile_social_timeline_failed", member_id=str(member_id))
        degraded_sections.append("social_timeline")

    try:
        # Messages sent
        if child_user_id:
            msgs_r = await db.execute(
                select(Message).where(
                    Message.sender_id == child_user_id,
                ).order_by(Message.created_at.desc()).limit(10)
            )
            for msg in msgs_r.scalars().all():
                timeline.append(TimelineItem(
                    id=msg.id,
                    source="social_message",
                    event_type="message",
                    title="Chat message",
                    detail=msg.content[:100] if msg.content else "",
                    platform="bhapi_social",
                    timestamp=msg.created_at.isoformat() if msg.created_at else "",
                ))
    except Exception:
        logger.exception("child_profile_messages_timeline_failed", member_id=str(member_id))
        degraded_sections.append("messages_timeline")

    try:
        # Risk events
        risk_r = await db.execute(
            select(RiskEvent).where(
                RiskEvent.member_id == member_id,
            ).order_by(RiskEvent.created_at.desc()).limit(10)
        )
        for re_item in risk_r.scalars().all():
            timeline.append(TimelineItem(
                id=re_item.id,
                source="risk",
                event_type="risk_event",
                title=f"Risk: {re_item.category}",
                detail="",
                severity=re_item.severity,
                timestamp=re_item.created_at.isoformat() if re_item.created_at else "",
            ))
    except Exception:
        logger.exception("child_profile_risk_timeline_failed", member_id=str(member_id))
        degraded_sections.append("risk_timeline")

    try:
        # Moderation decisions (for content authored by child)
        if child_user_id:
            # Get child's post IDs
            child_post_ids_r = await db.execute(
                select(SocialPost.id).where(SocialPost.author_id == child_user_id)
            )
            child_post_ids = [r[0] for r in child_post_ids_r.all()]
            if child_post_ids:
                mod_r = await db.execute(
                    select(ModerationQueue).where(
                        ModerationQueue.content_id.in_(child_post_ids),
                        ModerationQueue.status.in_(["rejected", "escalated"]),
                    ).order_by(ModerationQueue.created_at.desc()).limit(5)
                )
                for mq in mod_r.scalars().all():
                    timeline.append(TimelineItem(
                        id=mq.id,
                        source="moderation",
                        event_type="moderation_decision",
                        title=f"Content {mq.status}",
                        detail=f"{mq.content_type} moderation",
                        severity="high" if mq.status == "rejected" else "medium",
                        platform="bhapi_social",
                        timestamp=mq.created_at.isoformat() if mq.created_at else "",
                    ))
    except Exception:
        logger.exception("child_profile_moderation_timeline_failed", member_id=str(member_id))
        degraded_sections.append("moderation_timeline")

    # Sort timeline by timestamp descending
    timeline.sort(key=lambda t: t.timestamp, reverse=True)
    timeline = timeline[:50]  # cap at 50

    # --- Risk trend ---
    risk_trend_7d: list[RiskTrendPoint] = []
    risk_trend_30d: list[RiskTrendPoint] = []
    try:
        for days, trend_list in [(7, risk_trend_7d), (30, risk_trend_30d)]:
            for i in range(days - 1, -1, -1):
                day_start = (now - timedelta(days=i)).replace(
                    hour=0, minute=0, second=0, microsecond=0,
                )
                day_end = day_start + timedelta(days=1)

                total_r = await db.execute(
                    select(func.count(RiskEvent.id)).where(
                        RiskEvent.member_id == member_id,
                        RiskEvent.created_at >= day_start,
                        RiskEvent.created_at < day_end,
                    )
                )
                high_r = await db.execute(
                    select(func.count(RiskEvent.id)).where(
                        RiskEvent.member_id == member_id,
                        RiskEvent.created_at >= day_start,
                        RiskEvent.created_at < day_end,
                        RiskEvent.severity.in_(["critical", "high"]),
                    )
                )
                trend_list.append(RiskTrendPoint(
                    date=day_start.strftime("%Y-%m-%d"),
                    count=total_r.scalar() or 0,
                    high_count=high_r.scalar() or 0,
                ))
    except Exception:
        logger.exception("child_profile_risk_trend_failed", member_id=str(member_id))
        degraded_sections.append("risk_trend")

    # --- Platform breakdown ---
    platform_breakdown: list[PlatformBreakdown] = []
    try:
        platform_r = await db.execute(
            select(CaptureEvent.platform, func.count(CaptureEvent.id)).where(
                CaptureEvent.member_id == member_id,
                CaptureEvent.timestamp >= thirty_days_ago,
            ).group_by(CaptureEvent.platform).order_by(func.count(CaptureEvent.id).desc())
        )
        platform_rows = platform_r.all()

        # Add social activity as a platform
        social_event_count = 0
        if child_user_id:
            social_r = await db.execute(
                select(func.count(SocialPost.id)).where(
                    SocialPost.author_id == child_user_id,
                    SocialPost.created_at >= thirty_days_ago,
                )
            )
            social_event_count = social_r.scalar() or 0

        total_events = sum(r[1] for r in platform_rows) + social_event_count

        for name, count in platform_rows:
            pct = (count / total_events * 100) if total_events > 0 else 0
            platform_breakdown.append(PlatformBreakdown(
                platform=name, event_count=count, percentage=round(pct, 1),
            ))
        if social_event_count > 0:
            pct = (social_event_count / total_events * 100) if total_events > 0 else 0
            platform_breakdown.append(PlatformBreakdown(
                platform="bhapi_social", event_count=social_event_count,
                percentage=round(pct, 1),
            ))
    except Exception:
        logger.exception("child_profile_platform_breakdown_failed", member_id=str(member_id))
        degraded_sections.append("platform_breakdown")

    # --- Quick-action counts ---
    unresolved_alerts = 0
    pending_contacts = 0
    flagged_count = 0
    try:
        ua_r = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.member_id == member_id,
                Alert.status != "acknowledged",
            )
        )
        unresolved_alerts = ua_r.scalar() or 0
    except Exception:
        logger.exception("child_profile_unresolved_alerts_failed", member_id=str(member_id))
        degraded_sections.append("unresolved_alerts")

    try:
        if child_user_id:
            pc_r = await db.execute(
                select(func.count(Contact.id)).where(
                    or_(
                        Contact.requester_id == child_user_id,
                        Contact.target_id == child_user_id,
                    ),
                    Contact.status == "pending",
                )
            )
            pending_contacts = pc_r.scalar() or 0
    except Exception:
        logger.exception("child_profile_pending_contacts_failed", member_id=str(member_id))
        degraded_sections.append("pending_contacts")

    try:
        if child_user_id:
            fc_r = await db.execute(
                select(func.count(SocialPost.id)).where(
                    SocialPost.author_id == child_user_id,
                    SocialPost.moderation_status.in_(["rejected", "removed"]),
                )
            )
            flagged_count = fc_r.scalar() or 0
    except Exception:
        logger.exception("child_profile_flagged_count_failed", member_id=str(member_id))
        degraded_sections.append("flagged_content")

    return ChildProfileResponse(
        member_id=member.id,
        member_name=member.display_name,
        avatar_url=avatar_url,
        age_tier=age_tier,
        risk_score=risk_score,
        timeline=timeline,
        risk_trend_7d=risk_trend_7d,
        risk_trend_30d=risk_trend_30d,
        platform_breakdown=platform_breakdown,
        unresolved_alerts=unresolved_alerts,
        pending_contact_requests=pending_contacts,
        flagged_content_count=flagged_count,
        degraded_sections=degraded_sections,
    )
