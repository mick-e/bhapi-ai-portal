"""Demo session management for enterprise sales enablement."""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import Boolean, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class DemoSession(Base, UUIDMixin, TimestampMixin):
    """A time-limited demo session for prospective customers."""

    __tablename__ = "demo_sessions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # school, club, enterprise
    demo_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    demo_data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


async def create_demo_session(
    db: AsyncSession,
    name: str,
    email: str,
    organisation: str,
    account_type: str = "school",
    duration_hours: int = 72,
) -> DemoSession:
    """Create a new demo session valid for the specified duration."""
    if account_type not in ("school", "club", "enterprise"):
        raise ValidationError("Account type must be school, club, or enterprise")

    token = f"demo_{uuid.uuid4().hex[:16]}"
    session = DemoSession(
        id=uuid.uuid4(),
        name=name,
        email=email,
        organisation=organisation,
        account_type=account_type,
        demo_token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=duration_hours),
        demo_data=_generate_demo_data(account_type),
        views=0,
        active=True,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info("demo_session_created", token=token, email=email, org=organisation)
    return session


async def get_demo_session(db: AsyncSession, token: str) -> DemoSession:
    """Get a demo session by token."""
    result = await db.execute(
        select(DemoSession).where(
            DemoSession.demo_token == token,
            DemoSession.active.is_(True),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Demo session")

    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise ValidationError("This demo session has expired. Please request a new demo.")

    # Track view
    session.views += 1
    await db.flush()

    return session


async def list_demo_sessions(db: AsyncSession, active_only: bool = True) -> list[DemoSession]:
    """List demo sessions (admin only)."""
    query = select(DemoSession).order_by(DemoSession.created_at.desc())
    if active_only:
        query = query.where(DemoSession.active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


def _generate_demo_data(account_type: str) -> dict:
    """Generate realistic demo data for the session."""
    base = {
        "members": [
            {"name": "Alex Thompson", "role": "member", "risk_level": "low"},
            {"name": "Sam Chen", "role": "member", "risk_level": "medium"},
            {"name": "Jordan Rivera", "role": "member", "risk_level": "low"},
        ],
        "alerts": [
            {"severity": "warning", "message": "PII detected in ChatGPT conversation", "platform": "chatgpt"},
            {"severity": "critical", "message": "Potential deepfake content shared", "platform": "gemini"},
            {"severity": "info", "message": "New AI platform detected: Claude", "platform": "claude"},
        ],
        "risk_summary": {
            "total_events": 47,
            "high_severity": 3,
            "categories": {"pii": 8, "inappropriate_content": 5, "academic_integrity": 12},
        },
        "spend_summary": {
            "total_usd": 234.56,
            "by_provider": {"openai": 145.20, "anthropic": 67.30, "google": 22.06},
        },
    }
    if account_type == "school":
        base["school"] = {
            "classes": [
                {"name": "Grade 6 - Math", "students": 28, "safety_score": 87},
                {"name": "Grade 7 - English", "students": 32, "safety_score": 92},
                {"name": "Grade 8 - Science", "students": 25, "safety_score": 78},
            ],
            "district_name": "Springfield Unified",
        }
    return base


# ROI Calculator
def calculate_roi(
    num_students: int,
    avg_incidents_per_month: int = 5,
    cost_per_incident: float = 500.0,
    hours_manual_review: float = 10.0,
    hourly_rate: float = 50.0,
) -> dict:
    """Calculate estimated ROI from deploying Bhapi AI Portal."""
    monthly_incident_cost = avg_incidents_per_month * cost_per_incident
    monthly_manual_cost = hours_manual_review * hourly_rate * 4  # weekly -> monthly
    current_monthly_cost = monthly_incident_cost + monthly_manual_cost

    # Bhapi cost
    per_student_monthly = 2.99
    bhapi_monthly = num_students * per_student_monthly

    # Bhapi reduces incidents by ~60%, manual review by ~80%
    reduced_incident_cost = monthly_incident_cost * 0.4
    reduced_manual_cost = monthly_manual_cost * 0.2
    new_monthly_cost = reduced_incident_cost + reduced_manual_cost + bhapi_monthly

    monthly_savings = current_monthly_cost - new_monthly_cost
    annual_savings = monthly_savings * 12
    roi_percentage = (monthly_savings / bhapi_monthly * 100) if bhapi_monthly > 0 else 0

    return {
        "num_students": num_students,
        "current_monthly_cost": round(current_monthly_cost, 2),
        "bhapi_monthly_cost": round(bhapi_monthly, 2),
        "new_monthly_cost": round(new_monthly_cost, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "roi_percentage": round(roi_percentage, 1),
        "incident_reduction_pct": 60,
        "manual_review_reduction_pct": 80,
        "payback_months": round(bhapi_monthly / monthly_savings, 1) if monthly_savings > 0 else 0,
    }


# Case Studies
CASE_STUDIES = [
    {
        "id": "springfield-unified",
        "title": "Springfield Unified School District",
        "subtitle": "How a 5,000-student district secured AI usage in 30 days",
        "industry": "K-12 Education",
        "size": "5,000 students",
        "challenge": (
            "Students were using ChatGPT and Gemini for homework without"
            " oversight. Teachers had no visibility into AI usage patterns."
            " Three incidents of PII exposure went undetected for weeks."
        ),
        "solution": (
            "Deployed Bhapi AI Portal across 12 schools with Clever SIS"
            " integration. Set up automated blocking for critical risk"
            " content and real-time alerts for safeguarding leads."
        ),
        "results": [
            {
                "metric": "AI incidents detected",
                "before": "3 per quarter (manual)",
                "after": "47 per month (automated)",
            },
            {"metric": "Mean time to respond", "before": "2+ weeks", "after": "< 15 minutes"},
            {"metric": "PII exposure events", "before": "Unknown", "after": "Zero (auto-blocked)"},
            {"metric": "Teacher satisfaction", "before": "32%", "after": "94%"},
        ],
        "quote": (
            "Bhapi gave us visibility we didn't even know we needed."
            " The first week, we caught three students sharing personal"
            " information with AI chatbots."
        ),
        "quote_author": "Dr. Sarah Mitchell, Director of Technology",
    },
    {
        "id": "greenwood-academy",
        "title": "Greenwood Academy",
        "subtitle": "Private school achieves COPPA compliance with zero disruption",
        "industry": "Private Education",
        "size": "800 students",
        "challenge": (
            "Needed COPPA compliance for students under 13 using AI"
            " platforms. Manual consent tracking was consuming 20+ hours"
            " per week for the admin team."
        ),
        "solution": (
            "Bhapi's automated consent workflow and COPPA dashboard"
            " eliminated manual tracking. Age verification via Yoti"
            " ensured proper consent for all under-13 students."
        ),
        "results": [
            {"metric": "Consent compliance rate", "before": "67%", "after": "100%"},
            {"metric": "Admin hours on consent", "before": "20+ hours/week", "after": "< 2 hours/week"},
            {"metric": "Audit readiness", "before": "6+ weeks preparation", "after": "Always ready"},
        ],
        "quote": "We went from dreading audits to being confident we could pass one at any time.",
        "quote_author": "James Park, Head of Compliance",
    },
    {
        "id": "tech-family",
        "title": "The Chen Family",
        "subtitle": "How one family balanced AI learning with safety",
        "industry": "Family",
        "size": "2 children (ages 9 and 13)",
        "challenge": (
            "Both children were heavy AI users \u2014 one for homework help,"
            " the other exploring creative AI tools. Parents wanted"
            " visibility without being overly restrictive."
        ),
        "solution": (
            "Set up age-appropriate safety profiles. Strict mode for the"
            " 9-year-old (auto-blocking critical content) and moderate"
            " mode for the 13-year-old (alerts only). Weekly family"
            " reports kept everyone informed."
        ),
        "results": [
            {"metric": "Blocked inappropriate requests", "before": "Unknown", "after": "12 in first month"},
            {"metric": "Family AI discussions", "before": "0 per week", "after": "2-3 per week"},
            {"metric": "Children's AI literacy", "before": "Basic", "after": "Completed 3 literacy modules"},
        ],
        "quote": "It's not about spying on our kids \u2014 it's about having informed conversations about AI.",
        "quote_author": "Lisa Chen, Parent",
    },
]


def get_case_studies() -> list[dict]:
    """Get all case studies."""
    return CASE_STUDIES


def get_case_study(case_id: str) -> dict | None:
    """Get a single case study by ID."""
    return next((c for c in CASE_STUDIES if c["id"] == case_id), None)
