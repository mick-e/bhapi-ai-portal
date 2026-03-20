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
