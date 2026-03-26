"""Governance module API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.governance.eu_ai_act import (
    create_conformity_assessment,
    generate_registration_payload,
    generate_tech_documentation,
    get_registration_status,
    run_bias_test,
    run_risk_management_assessment,
    submit_registration,
)
from src.governance.eu_ai_act import (
    get_compliance_status as get_eu_ai_act_status,
)
from src.governance.ohio import (
    customize_ohio_policy,
    generate_board_report,
    get_ohio_compliance_status,
    import_tools_csv,
)
from src.governance.schemas import (
    ComplianceDashboardResponse,
    EuAiActAssessmentRequest,
    EuAiActAssessmentResponse,
    EuAiActBiasTestRequest,
    EuAiActBiasTestResponse,
    EuAiActComplianceStatusResponse,
    EuAiActRegistrationGenerateRequest,
    EuAiActRegistrationPayloadResponse,
    EuAiActRegistrationStatusResponse,
    EuAiActRegistrationSubmitRequest,
    EuAiActRegistrationSubmitResponse,
    EuAiActRiskRequest,
    EuAiActRiskResponse,
    EuAiActTechDocsRequest,
    EuAiActTechDocsResponse,
    OhioBoardReportResponse,
    OhioComplianceStatusResponse,
    OhioCustomizeRequest,
    OhioCustomizeResponse,
    OhioImportToolsRequest,
    OhioImportToolsResponse,
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


# ---------------------------------------------------------------------------
# Ohio-specific endpoints
# ---------------------------------------------------------------------------


@router.post("/ohio/customize", response_model=OhioCustomizeResponse, status_code=201)
async def ohio_customize_endpoint(
    data: OhioCustomizeRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Customize Ohio AI policy template with district-specific requirements."""
    result = await customize_ohio_policy(
        db,
        school_id=data.school_id,
        district_name=data.district_name,
        additional_requirements=data.additional_requirements,
        approved_tools=data.approved_tools,
        actor_id=auth.user_id,
    )
    return result


@router.post("/ohio/import-tools", response_model=OhioImportToolsResponse)
async def ohio_import_tools_endpoint(
    data: OhioImportToolsRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import AI tools from CSV data."""
    return await import_tools_csv(
        db,
        school_id=data.school_id,
        csv_data=data.csv_data,
        actor_id=auth.user_id,
    )


@router.get("/ohio/board-report", response_model=OhioBoardReportResponse)
async def ohio_board_report_endpoint(
    school_id: UUID = Query(..., description="School group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a board-ready compliance report for Ohio mandate."""
    return await generate_board_report(db, school_id)


@router.get("/ohio/status", response_model=OhioComplianceStatusResponse)
async def ohio_status_endpoint(
    school_id: UUID = Query(..., description="School group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check Ohio compliance status for a school."""
    return await get_ohio_compliance_status(db, school_id)


# ---------------------------------------------------------------------------
# EU AI Act endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/eu-ai-act/assessment",
    response_model=EuAiActAssessmentResponse,
    status_code=201,
)
async def eu_ai_act_create_assessment(
    data: EuAiActAssessmentRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a conformity assessment per EU AI Act Articles 9-15."""
    return await create_conformity_assessment(
        db,
        group_id=data.group_id,
        assessor=data.assessor,
    )


@router.get(
    "/eu-ai-act/assessment",
    response_model=EuAiActComplianceStatusResponse,
)
async def eu_ai_act_get_assessment(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current EU AI Act compliance status including assessment."""
    return await get_eu_ai_act_status(db, group_id)


@router.post(
    "/eu-ai-act/tech-docs",
    response_model=EuAiActTechDocsResponse,
    status_code=201,
)
async def eu_ai_act_generate_tech_docs(
    data: EuAiActTechDocsRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate technical documentation per EU AI Act Annex IV."""
    return await generate_tech_documentation(
        db,
        group_id=data.group_id,
        system_name=data.system_name,
        system_description=data.system_description,
    )


@router.post(
    "/eu-ai-act/risk-management",
    response_model=EuAiActRiskResponse,
    status_code=201,
)
async def eu_ai_act_risk_management(
    data: EuAiActRiskRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a risk management record per EU AI Act Article 9."""
    return await run_risk_management_assessment(
        db,
        group_id=data.group_id,
        risk_type=data.risk_type,
        description=data.description,
        severity=data.severity,
        likelihood=data.likelihood,
        mitigation=data.mitigation,
    )


@router.post(
    "/eu-ai-act/bias-test",
    response_model=EuAiActBiasTestResponse,
    status_code=201,
)
async def eu_ai_act_bias_test(
    data: EuAiActBiasTestRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run bias testing per EU AI Act Article 10."""
    return await run_bias_test(
        db,
        group_id=data.group_id,
        model_id=data.model_id,
        test_data=data.test_data,
    )


@router.get(
    "/eu-ai-act/status",
    response_model=EuAiActComplianceStatusResponse,
)
async def eu_ai_act_status(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get overall EU AI Act compliance readiness status."""
    return await get_eu_ai_act_status(db, group_id)


# ---------------------------------------------------------------------------
# EU AI Act Registration endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/eu-ai-act/registration/generate",
    response_model=EuAiActRegistrationPayloadResponse,
)
async def eu_ai_act_generate_registration(
    data: EuAiActRegistrationGenerateRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate EU database registration payload with all required fields."""
    return await generate_registration_payload(db, group_id=data.group_id)


@router.post(
    "/eu-ai-act/registration/submit",
    response_model=EuAiActRegistrationSubmitResponse,
)
async def eu_ai_act_submit_registration(
    data: EuAiActRegistrationSubmitRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit EU database registration."""
    return await submit_registration(db, group_id=data.group_id)


@router.get(
    "/eu-ai-act/registration/status",
    response_model=EuAiActRegistrationStatusResponse,
)
async def eu_ai_act_registration_status(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get EU database registration status."""
    return await get_registration_status(db, group_id=group_id)
