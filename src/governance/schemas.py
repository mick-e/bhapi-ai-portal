"""Governance module Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PolicyCreate(BaseSchema):
    """Create a new governance policy."""

    school_id: UUID
    state_code: str = Field(max_length=2, min_length=2)
    policy_type: str = Field(max_length=30)
    content: dict


class PolicyUpdate(BaseSchema):
    """Update an existing governance policy."""

    content: dict


class TemplateGenerateRequest(BaseSchema):
    """Request to generate a policy template."""

    state_code: str = Field(max_length=2, min_length=2)
    policy_type: str = Field(max_length=30)


class ToolCreate(BaseSchema):
    """Add an AI tool to the inventory."""

    school_id: UUID
    tool_name: str = Field(max_length=200)
    vendor: str = Field(max_length=200)
    risk_level: str = Field(max_length=20)  # low, medium, high
    approval_status: str = Field(max_length=20)  # pending, approved, denied


class RiskAssessmentRequest(BaseSchema):
    """Request to run a risk assessment."""

    school_id: UUID


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PolicyResponse(BaseSchema):
    """Governance policy response."""

    id: UUID
    school_id: UUID
    state_code: str
    policy_type: str
    content: dict
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class AuditResponse(BaseSchema):
    """Governance audit trail entry."""

    id: UUID
    policy_id: UUID
    action: str
    actor_id: UUID
    diff: dict | None = None
    timestamp: datetime


class TemplateResponse(BaseSchema):
    """Generated policy template."""

    state_code: str
    policy_type: str
    template: dict


class ToolResponse(BaseSchema):
    """AI tool inventory entry (stored as a policy with type=tool_inventory)."""

    id: UUID
    school_id: UUID
    tool_name: str
    vendor: str
    risk_level: str
    approval_status: str
    created_at: datetime
    updated_at: datetime


class RiskFinding(BaseSchema):
    """A single risk finding."""

    description: str
    deduction: int


class RiskAssessmentResponse(BaseSchema):
    """Risk assessment result."""

    school_id: UUID
    score: int
    findings: list[RiskFinding]


class ComplianceDashboardResponse(BaseSchema):
    """Compliance dashboard data."""

    school_id: UUID
    policy_count: int
    tool_count: int
    risk_score: int
    recent_audits: list[AuditResponse]
    policy_coverage: list[str]
    missing_policies: list[str]


class PaginatedPolicies(BaseSchema):
    """Paginated list of policies."""

    items: list[PolicyResponse]
    total: int
    page: int
    page_size: int


class PaginatedAudits(BaseSchema):
    """Paginated list of audits."""

    items: list[AuditResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Ohio-specific schemas
# ---------------------------------------------------------------------------


class OhioCustomizeRequest(BaseSchema):
    """Request to customize Ohio policy template for a district."""

    school_id: UUID
    district_name: str = Field(max_length=200, min_length=1)
    additional_requirements: list[str] = Field(default_factory=list)
    approved_tools: list[str] = Field(default_factory=list)


class OhioCustomizeResponse(BaseSchema):
    """Response from Ohio policy customization."""

    state_code: str
    policy_id: str
    content: dict
    status: str
    version: int


class OhioImportToolsRequest(BaseSchema):
    """Request to import AI tools from CSV."""

    school_id: UUID
    csv_data: str = Field(min_length=1)


class OhioImportToolsResponse(BaseSchema):
    """Response from CSV tool import."""

    imported: int
    errors: list[dict]
    total_rows: int
    import_log_id: str


class OhioBoardReportResponse(BaseSchema):
    """Board-ready compliance report."""

    format: str
    generated_at: str
    state_code: str
    district_name: str | None = None
    compliance_score: int
    is_compliant: bool
    tool_inventory_count: int
    tools_by_risk: dict
    tools_by_status: dict
    policy_count: int
    policy_coverage: list[str]
    missing_policies: list[str]
    risk_findings: list[dict]
    audit_count: int
    recent_actions: list[dict]


class OhioComplianceStatusResponse(BaseSchema):
    """Ohio compliance status check."""

    school_id: str
    state_code: str
    overall_status: str
    compliance_deadline: str
    policy_status: dict
    active_policy_count: int
    tool_count: int
    ready_for_board: bool


# ---------------------------------------------------------------------------
# EU AI Act schemas
# ---------------------------------------------------------------------------


class EuAiActAssessmentRequest(BaseSchema):
    """Request to create a conformity assessment."""

    group_id: UUID
    assessor: str = Field(max_length=200, min_length=1)


class EuAiActAssessmentStatusRequest(BaseSchema):
    """Request to update assessment status."""

    status: str = Field(max_length=20)


class EuAiActAssessmentResponse(BaseSchema):
    """Conformity assessment response."""

    assessment_id: str
    group_id: str
    version: int
    status: str
    sections: dict
    assessor: str
    assessed_at: str | None = None


class EuAiActTechDocsRequest(BaseSchema):
    """Request to generate technical documentation."""

    group_id: UUID
    system_name: str = Field(max_length=200, min_length=1)
    system_description: str = Field(max_length=2000, min_length=1)


class EuAiActTechDocsResponse(BaseSchema):
    """Technical documentation response."""

    doc_id: str
    group_id: str
    version: int
    system_name: str
    sections: dict
    generated_at: str | None = None


class EuAiActRiskRequest(BaseSchema):
    """Request to create a risk management record."""

    group_id: UUID
    risk_type: str = Field(max_length=50)
    description: str = Field(max_length=2000, min_length=1)
    severity: str = Field(max_length=20)
    likelihood: str = Field(max_length=20)
    mitigation: str = Field(max_length=2000, min_length=1)


class EuAiActRiskResponse(BaseSchema):
    """Risk management record response."""

    record_id: str
    group_id: str
    risk_type: str
    description: str
    severity: str
    likelihood: str
    mitigation: str
    residual_risk: str
    reviewed_at: str | None = None


class EuAiActBiasTestRequest(BaseSchema):
    """Request to run bias testing."""

    group_id: UUID
    model_id: str = Field(max_length=200, min_length=1)
    test_data: dict


class EuAiActBiasTestResponse(BaseSchema):
    """Bias test result response."""

    test_id: str
    group_id: str
    model_id: str
    test_data_hash: str
    results: dict
    overall_score: float
    tested_at: str | None = None


class EuAiActComplianceStatusResponse(BaseSchema):
    """EU AI Act compliance status response."""

    group_id: str
    overall_readiness_score: int
    status: str
    components: dict
    eu_ai_act_deadline: str
