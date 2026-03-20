"""Governance module API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.governance.schemas import (
    ComplianceDashboardResponse,
    PaginatedAudits,
    PaginatedPolicies,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    TemplateGenerateRequest,
    TemplateResponse,
    ToolCreate,
    ToolResponse,
)
from src.governance.service import (
    add_tool_to_inventory,
    archive_policy,
    create_policy,
    generate_template,
    get_audit_trail,
    get_compliance_dashboard,
    get_policy,
    list_policies,
    list_tool_inventory,
    run_risk_assessment,
    update_policy,
)
from src.schemas import GroupContext

router = APIRouter()


# ---------------------------------------------------------------------------
# Policy endpoints
# ---------------------------------------------------------------------------


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy_endpoint(
    data: PolicyCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new governance policy."""
    return await create_policy(
        db,
        school_id=data.school_id,
        state_code=data.state_code,
        policy_type=data.policy_type,
        content=data.content,
        actor_id=auth.user_id,
    )


@router.get("/policies", response_model=PaginatedPolicies)
async def list_policies_endpoint(
    school_id: UUID = Query(..., description="School group ID"),
    status: str | None = Query(None, description="Filter by status"),
    policy_type: str | None = Query(None, description="Filter by policy type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List governance policies for a school."""
    return await list_policies(
        db,
        school_id=school_id,
        status=status,
        policy_type=policy_type,
        page=page,
        page_size=page_size,
    )


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy_endpoint(
    policy_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single governance policy."""
    return await get_policy(db, policy_id)


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy_endpoint(
    policy_id: UUID,
    data: PolicyUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a governance policy."""
    return await update_policy(db, policy_id, data.content, auth.user_id)


@router.patch("/policies/{policy_id}/archive", response_model=PolicyResponse)
async def archive_policy_endpoint(
    policy_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a governance policy."""
    return await archive_policy(db, policy_id, auth.user_id)


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------


@router.post("/templates/generate", response_model=TemplateResponse)
async def generate_template_endpoint(
    data: TemplateGenerateRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a policy template for a specific state and policy type."""
    return generate_template(data.state_code, data.policy_type)


# ---------------------------------------------------------------------------
# Tool inventory endpoints
# ---------------------------------------------------------------------------


@router.post("/tools", response_model=ToolResponse, status_code=201)
async def add_tool_endpoint(
    data: ToolCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an AI tool to the inventory."""
    return await add_tool_to_inventory(
        db,
        school_id=data.school_id,
        tool_name=data.tool_name,
        vendor=data.vendor,
        risk_level=data.risk_level,
        approval_status=data.approval_status,
        actor_id=auth.user_id,
    )


@router.get("/tools", response_model=list[ToolResponse])
async def list_tools_endpoint(
    school_id: UUID = Query(..., description="School group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI tool inventory for a school."""
    return await list_tool_inventory(db, school_id)


# ---------------------------------------------------------------------------
# Risk assessment endpoints
# ---------------------------------------------------------------------------


@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def risk_assessment_endpoint(
    data: RiskAssessmentRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a risk assessment for a school."""
    return await run_risk_assessment(db, data.school_id)


# ---------------------------------------------------------------------------
# Dashboard endpoints
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=ComplianceDashboardResponse)
async def dashboard_endpoint(
    school_id: UUID = Query(..., description="School group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance dashboard data for a school."""
    return await get_compliance_dashboard(db, school_id)


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------


@router.get("/audits/{policy_id}", response_model=PaginatedAudits)
async def audit_trail_endpoint(
    policy_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit trail for a governance policy."""
    return await get_audit_trail(db, policy_id, page=page, page_size=page_size)
