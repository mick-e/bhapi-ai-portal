"""Portal BFF API endpoints."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id as _resolve_group_id
from src.exceptions import BhapiException
from src.groups.privacy import get_child_dashboard
from src.portal.schemas import DashboardResponse, GroupSettingsResponse, UpdateGroupSettingsRequest
from src.portal.service import get_dashboard, get_group_settings, update_group_settings
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get primary dashboard data (FR-010)."""
    try:
        return await get_dashboard(db, _resolve_group_id(group_id, auth), auth.user_id)
    except BhapiException:
        raise
    except Exception:
        logger.exception("dashboard_endpoint_failed", user_id=str(auth.user_id))
        return DashboardResponse(degraded_sections=["all"])


@router.get("/settings", response_model=GroupSettingsResponse)
async def get_settings(
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get group settings."""
    return await get_group_settings(db, _resolve_group_id(group_id, auth), auth.user_id)


@router.patch("/settings", response_model=GroupSettingsResponse)
async def patch_settings(
    data: UpdateGroupSettingsRequest,
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update group settings."""
    return await update_group_settings(db, _resolve_group_id(group_id, auth), auth.user_id, data)


@router.get("/child-dashboard")
async def child_dashboard(
    member_id: UUID = Query(..., description="The member (child) ID"),
    group_id: UUID | None = Query(None, description="Group ID (defaults to user's primary group)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get child's own filtered dashboard view."""
    return await get_child_dashboard(db, _resolve_group_id(group_id, auth), member_id)


# ─── Onboarding ──────────────────────────────────────────────────────────────


@router.get("/onboarding")
async def get_onboarding(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get onboarding progress for the current user."""
    from src.portal.onboarding import get_onboarding_progress
    return await get_onboarding_progress(db, auth.user_id)


@router.post("/onboarding/complete-step")
async def complete_step(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an onboarding step as complete."""
    from src.portal.onboarding import complete_onboarding_step
    step_key = data.get("step_key", "")
    return await complete_onboarding_step(db, auth.user_id, step_key)


@router.post("/onboarding/dismiss")
async def dismiss_onboarding_endpoint(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss onboarding wizard."""
    from src.portal.onboarding import dismiss_onboarding
    return await dismiss_onboarding(db, auth.user_id)


# ─── Demo Sessions (enterprise sales) ──────────────────────────────────────


@router.post("/demo", status_code=201)
async def create_demo(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Create a demo session (public, no auth required)."""
    from src.portal.demo import create_demo_session

    session = await create_demo_session(
        db,
        name=data.get("name", ""),
        email=data.get("email", ""),
        organisation=data.get("organisation", ""),
        account_type=data.get("account_type", "school"),
    )
    return {
        "demo_token": session.demo_token,
        "expires_at": session.expires_at.isoformat(),
        "organisation": session.organisation,
    }


@router.get("/demo/{token}")
async def get_demo(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get demo session data (public, no auth required)."""
    from src.portal.demo import get_demo_session

    session = await get_demo_session(db, token)
    return {
        "name": session.name,
        "organisation": session.organisation,
        "account_type": session.account_type,
        "demo_data": session.demo_data,
        "expires_at": session.expires_at.isoformat(),
        "views": session.views,
    }


# ─── ROI Calculator (public) ───────────────────────────────────────────────


@router.get("/roi-calculator")
async def roi_calculator(
    num_students: int = Query(100, ge=1, le=100000),
    avg_incidents: int = Query(5, ge=0, le=100),
    cost_per_incident: float = Query(500.0, ge=0),
    hours_manual_review: float = Query(10.0, ge=0),
    hourly_rate: float = Query(50.0, ge=0),
):
    """Calculate ROI for deploying Bhapi (public, no auth required)."""
    from src.portal.demo import calculate_roi

    return calculate_roi(
        num_students=num_students,
        avg_incidents_per_month=avg_incidents,
        cost_per_incident=cost_per_incident,
        hours_manual_review=hours_manual_review,
        hourly_rate=hourly_rate,
    )


# ─── Case Studies (public) ─────────────────────────────────────────────────


@router.get("/case-studies")
async def list_case_studies():
    """List all case studies (public, no auth required)."""
    from src.portal.demo import get_case_studies

    return {"case_studies": get_case_studies()}


@router.get("/case-studies/{case_id}")
async def get_case_study_endpoint(case_id: str):
    """Get a single case study (public, no auth required)."""
    from src.portal.demo import get_case_study
    from src.exceptions import NotFoundError

    study = get_case_study(case_id)
    if not study:
        raise NotFoundError(f"Case study '{case_id}'")
    return study


# ─── Unified Dashboard ──────────────────────────────────────────────────────


@router.get("/unified-dashboard")
async def unified_dashboard(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unified cross-product dashboard data."""
    from src.portal.unified import get_unified_dashboard

    gid = _resolve_group_id(None, auth)
    return await get_unified_dashboard(db, gid)


# ─── Blog (public, SEO) ────────────────────────────────────────────────────


@router.get("/blog")
async def list_blog_posts(
    category: str | None = Query(None),
    tag: str | None = Query(None),
):
    """List blog posts (public, no auth required)."""
    from src.portal.blog import get_blog_posts
    return {"posts": get_blog_posts(category=category, tag=tag)}


@router.get("/blog/{slug}")
async def get_blog_post_endpoint(slug: str):
    """Get a single blog post (public, no auth required)."""
    from src.portal.blog import get_blog_post
    from src.exceptions import NotFoundError
    post = get_blog_post(slug)
    if not post:
        raise NotFoundError(f"Blog post '{slug}'")
    return post
