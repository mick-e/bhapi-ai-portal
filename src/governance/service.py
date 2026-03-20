"""Governance module — business logic."""

from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.governance.models import GovernanceAudit, GovernancePolicy
from src.governance.schemas import (
    AuditResponse,
    ComplianceDashboardResponse,
    PaginatedAudits,
    PaginatedPolicies,
    PolicyResponse,
    RiskAssessmentResponse,
    RiskFinding,
    TemplateResponse,
    ToolResponse,
)

logger = structlog.get_logger()

# Required policy types for compliance
REQUIRED_POLICY_TYPES = ["ai_usage", "risk_assessment", "governance"]


# ---------------------------------------------------------------------------
# Policy CRUD
# ---------------------------------------------------------------------------


async def create_policy(
    db: AsyncSession,
    school_id: UUID,
    state_code: str,
    policy_type: str,
    content: dict,
    actor_id: UUID,
) -> PolicyResponse:
    """Create a versioned governance policy."""
    policy = GovernancePolicy(
        id=uuid4(),
        school_id=school_id,
        state_code=state_code,
        policy_type=policy_type,
        content=content,
        status="draft",
        version=1,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)

    # Audit trail
    audit = GovernanceAudit(
        id=uuid4(),
        policy_id=policy.id,
        action="created",
        actor_id=actor_id,
        diff=None,
    )
    db.add(audit)
    await db.flush()

    logger.info(
        "governance_policy_created",
        policy_id=str(policy.id),
        school_id=str(school_id),
        policy_type=policy_type,
    )

    return _policy_to_response(policy)


async def update_policy(
    db: AsyncSession,
    policy_id: UUID,
    content: dict,
    actor_id: UUID,
) -> PolicyResponse:
    """Update a policy, increment version. Creates audit with diff."""
    policy = await _get_policy_or_404(db, policy_id)

    if policy.status == "archived":
        raise ValidationError("Cannot update an archived policy.")

    old_content = policy.content
    policy.content = content
    policy.version += 1
    await db.flush()
    await db.refresh(policy)

    # Audit trail with diff
    audit = GovernanceAudit(
        id=uuid4(),
        policy_id=policy.id,
        action="updated",
        actor_id=actor_id,
        diff={"old": old_content, "new": content},
    )
    db.add(audit)
    await db.flush()

    logger.info(
        "governance_policy_updated",
        policy_id=str(policy.id),
        version=policy.version,
    )

    return _policy_to_response(policy)


async def get_policy(db: AsyncSession, policy_id: UUID) -> PolicyResponse:
    """Get a single policy by ID."""
    policy = await _get_policy_or_404(db, policy_id)
    return _policy_to_response(policy)


async def list_policies(
    db: AsyncSession,
    school_id: UUID,
    status: str | None = None,
    policy_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedPolicies:
    """List policies for a school with optional filters."""
    query = select(GovernancePolicy).where(
        GovernancePolicy.school_id == school_id,
    )

    if status:
        query = query.where(GovernancePolicy.status == status)
    if policy_type:
        query = query.where(GovernancePolicy.policy_type == policy_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(GovernancePolicy.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    policies = list(result.scalars().all())

    return PaginatedPolicies(
        items=[_policy_to_response(p) for p in policies],
        total=total,
        page=page,
        page_size=page_size,
    )


async def archive_policy(
    db: AsyncSession,
    policy_id: UUID,
    actor_id: UUID,
) -> PolicyResponse:
    """Archive a policy."""
    policy = await _get_policy_or_404(db, policy_id)

    if policy.status == "archived":
        raise ValidationError("Policy is already archived.")

    policy.status = "archived"
    await db.flush()
    await db.refresh(policy)

    audit = GovernanceAudit(
        id=uuid4(),
        policy_id=policy.id,
        action="archived",
        actor_id=actor_id,
        diff=None,
    )
    db.add(audit)
    await db.flush()

    logger.info("governance_policy_archived", policy_id=str(policy.id))

    return _policy_to_response(policy)


# ---------------------------------------------------------------------------
# Template generation
# ---------------------------------------------------------------------------


def generate_template(state_code: str, policy_type: str) -> TemplateResponse:
    """Generate a state-specific policy template."""
    templates = _get_templates(state_code, policy_type)
    return TemplateResponse(
        state_code=state_code,
        policy_type=policy_type,
        template=templates,
    )


def _get_templates(state_code: str, policy_type: str) -> dict:
    """Return template content based on state and policy type."""
    if state_code == "OH":
        return _ohio_templates(policy_type)
    # Generic template for other states
    return _generic_template(policy_type)


def _ohio_templates(policy_type: str) -> dict:
    """Ohio AI mandate templates."""
    if policy_type == "ai_usage":
        return {
            "title": "Ohio AI Usage Policy",
            "purpose_statement": (
                "This policy establishes guidelines for the responsible use of "
                "artificial intelligence tools in our school district, as required "
                "by the Ohio AI mandate."
            ),
            "approved_tools": [
                {"name": "[Tool Name]", "vendor": "[Vendor]", "approved_date": "[Date]"},
            ],
            "prohibited_uses": [
                "Using AI to complete graded assignments without disclosure",
                "Sharing student personally identifiable information with AI tools",
                "Using AI tools not on the approved list",
                "Bypassing content filters or safety controls",
            ],
            "student_data_protection": {
                "requirements": [
                    "All AI tools must comply with FERPA and COPPA",
                    "Student data must not be used for AI model training",
                    "Data retention must not exceed the school year",
                    "Parents must be notified of AI tool usage",
                ],
            },
            "staff_training": {
                "requirements": [
                    "Annual AI literacy training for all staff",
                    "AI ethics module completion before tool access",
                    "Ongoing professional development on AI in education",
                ],
            },
            "review_schedule": {
                "frequency": "annual",
                "minimum_review": "Annual review required by Ohio mandate",
                "next_review_date": "[Set date within 12 months]",
            },
            "incident_response": {
                "steps": [
                    "Identify and document the AI-related incident",
                    "Notify school administration within 24 hours",
                    "Suspend access to the involved AI tool",
                    "Conduct investigation and root cause analysis",
                    "Report to parents if student data is affected",
                    "Update policies to prevent recurrence",
                ],
            },
        }
    elif policy_type == "tool_inventory":
        return {
            "title": "Ohio AI Tool Inventory Template",
            "description": "Inventory of all AI tools used within the school district.",
            "fields": [
                "tool_name", "vendor", "purpose", "data_collected",
                "risk_level", "approval_status", "review_date",
            ],
            "risk_levels": ["low", "medium", "high"],
            "approval_statuses": ["pending", "approved", "denied"],
        }
    elif policy_type == "risk_assessment":
        return {
            "title": "Ohio AI Risk Assessment Template",
            "description": "Risk assessment framework for AI tools in education.",
            "categories": [
                "Student data privacy",
                "Algorithmic bias",
                "Academic integrity",
                "Accessibility",
                "Content safety",
            ],
            "scoring": "Each category scored 1-5, total maximum 25",
        }
    elif policy_type == "governance":
        return {
            "title": "Ohio AI Governance Framework",
            "description": "Governance structure for AI oversight in the school district.",
            "roles": [
                {"role": "AI Governance Lead", "responsibilities": "Overall AI policy oversight"},
                {"role": "Data Protection Officer", "responsibilities": "Student data compliance"},
                {"role": "Technology Director", "responsibilities": "Tool evaluation and deployment"},
            ],
            "review_frequency": "Quarterly reviews, annual comprehensive audit",
        }
    return _generic_template(policy_type)


def _generic_template(policy_type: str) -> dict:
    """Generic template for non-Ohio states."""
    return {
        "title": f"AI {policy_type.replace('_', ' ').title()} Policy",
        "description": f"Template for {policy_type.replace('_', ' ')} policy.",
        "sections": [
            "Purpose and scope",
            "Definitions",
            "Policy guidelines",
            "Compliance requirements",
            "Review and update schedule",
        ],
    }


# ---------------------------------------------------------------------------
# Tool inventory
# ---------------------------------------------------------------------------


async def add_tool_to_inventory(
    db: AsyncSession,
    school_id: UUID,
    tool_name: str,
    vendor: str,
    risk_level: str,
    approval_status: str,
    actor_id: UUID,
) -> ToolResponse:
    """Add an AI tool to the inventory (stored as governance_policy with type=tool_inventory)."""
    if risk_level not in ("low", "medium", "high"):
        raise ValidationError("risk_level must be one of: low, medium, high")
    if approval_status not in ("pending", "approved", "denied"):
        raise ValidationError("approval_status must be one of: pending, approved, denied")

    content = {
        "tool_name": tool_name,
        "vendor": vendor,
        "risk_level": risk_level,
        "approval_status": approval_status,
    }

    policy = GovernancePolicy(
        id=uuid4(),
        school_id=school_id,
        state_code="--",  # tool inventory is state-agnostic
        policy_type="tool_inventory",
        content=content,
        status="active",
        version=1,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)

    # Audit
    audit = GovernanceAudit(
        id=uuid4(),
        policy_id=policy.id,
        action="tool_added",
        actor_id=actor_id,
        diff=None,
    )
    db.add(audit)
    await db.flush()

    logger.info(
        "governance_tool_added",
        tool_name=tool_name,
        school_id=str(school_id),
    )

    return _tool_to_response(policy)


async def list_tool_inventory(
    db: AsyncSession,
    school_id: UUID,
) -> list[ToolResponse]:
    """List all AI tools for a school."""
    result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type == "tool_inventory",
        ).order_by(GovernancePolicy.created_at.desc())
    )
    tools = list(result.scalars().all())
    return [_tool_to_response(t) for t in tools]


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


async def run_risk_assessment(
    db: AsyncSession,
    school_id: UUID,
) -> RiskAssessmentResponse:
    """Score based on tool and policy coverage. Returns score 0-100 and findings."""
    findings: list[RiskFinding] = []
    score = 100

    # Get all tools
    tools_result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type == "tool_inventory",
        )
    )
    tools = list(tools_result.scalars().all())

    # Get all non-tool policies
    policies_result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type != "tool_inventory",
            GovernancePolicy.status != "archived",
        )
    )
    policies = list(policies_result.scalars().all())
    policy_types = {p.policy_type for p in policies}

    # Check tools without policies: -10 each
    if tools and "ai_usage" not in policy_types:
        for tool in tools:
            deduction = 10
            score -= deduction
            findings.append(RiskFinding(
                description=f"Tool '{tool.content.get('tool_name', 'unknown')}' has no AI usage policy",
                deduction=deduction,
            ))

    # Check tools with high risk not approved: -20 each
    for tool in tools:
        content = tool.content or {}
        if content.get("risk_level") == "high" and content.get("approval_status") != "approved":
            deduction = 20
            score -= deduction
            findings.append(RiskFinding(
                description=f"High-risk tool '{content.get('tool_name', 'unknown')}' is not approved",
                deduction=deduction,
            ))

    # Check missing required policy types: -15 each
    for req_type in REQUIRED_POLICY_TYPES:
        if req_type not in policy_types:
            deduction = 15
            score -= deduction
            findings.append(RiskFinding(
                description=f"Missing required policy type: {req_type}",
                deduction=deduction,
            ))

    # Clamp to 0-100
    score = max(0, min(100, score))

    logger.info(
        "governance_risk_assessment",
        school_id=str(school_id),
        score=score,
        finding_count=len(findings),
    )

    return RiskAssessmentResponse(
        school_id=school_id,
        score=score,
        findings=findings,
    )


# ---------------------------------------------------------------------------
# Compliance dashboard
# ---------------------------------------------------------------------------


async def get_compliance_dashboard(
    db: AsyncSession,
    school_id: UUID,
) -> ComplianceDashboardResponse:
    """Returns compliance dashboard data for a school."""
    # Policy count (non-tool, non-archived)
    policy_count_result = await db.execute(
        select(func.count()).select_from(
            select(GovernancePolicy).where(
                GovernancePolicy.school_id == school_id,
                GovernancePolicy.policy_type != "tool_inventory",
                GovernancePolicy.status != "archived",
            ).subquery()
        )
    )
    policy_count = policy_count_result.scalar() or 0

    # Tool count
    tool_count_result = await db.execute(
        select(func.count()).select_from(
            select(GovernancePolicy).where(
                GovernancePolicy.school_id == school_id,
                GovernancePolicy.policy_type == "tool_inventory",
            ).subquery()
        )
    )
    tool_count = tool_count_result.scalar() or 0

    # Risk score
    risk = await run_risk_assessment(db, school_id)

    # Policy coverage
    coverage_result = await db.execute(
        select(GovernancePolicy.policy_type).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type != "tool_inventory",
            GovernancePolicy.status != "archived",
        ).distinct()
    )
    policy_coverage = [row[0] for row in coverage_result.all()]

    # Missing policies
    missing_policies = [t for t in REQUIRED_POLICY_TYPES if t not in policy_coverage]

    # Recent audits (last 10)
    audit_result = await db.execute(
        select(GovernanceAudit)
        .join(GovernancePolicy, GovernanceAudit.policy_id == GovernancePolicy.id)
        .where(GovernancePolicy.school_id == school_id)
        .order_by(GovernanceAudit.timestamp.desc())
        .limit(10)
    )
    recent_audits = [_audit_to_response(a) for a in audit_result.scalars().all()]

    return ComplianceDashboardResponse(
        school_id=school_id,
        policy_count=policy_count,
        tool_count=tool_count,
        risk_score=risk.score,
        recent_audits=recent_audits,
        policy_coverage=policy_coverage,
        missing_policies=missing_policies,
    )


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


async def get_audit_trail(
    db: AsyncSession,
    policy_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedAudits:
    """List audits for a policy."""
    # Verify policy exists
    await _get_policy_or_404(db, policy_id)

    query = select(GovernanceAudit).where(
        GovernanceAudit.policy_id == policy_id,
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(GovernanceAudit.timestamp.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    audits = list(result.scalars().all())

    return PaginatedAudits(
        items=[_audit_to_response(a) for a in audits],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_policy_or_404(db: AsyncSession, policy_id: UUID) -> GovernancePolicy:
    """Fetch a policy by ID or raise NotFoundError."""
    result = await db.execute(
        select(GovernancePolicy).where(GovernancePolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise NotFoundError("GovernancePolicy", str(policy_id))
    return policy


def _policy_to_response(policy: GovernancePolicy) -> PolicyResponse:
    """Convert model to response schema."""
    return PolicyResponse(
        id=policy.id,
        school_id=policy.school_id,
        state_code=policy.state_code,
        policy_type=policy.policy_type,
        content=policy.content,
        status=policy.status,
        version=policy.version,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _tool_to_response(policy: GovernancePolicy) -> ToolResponse:
    """Convert a tool_inventory policy to ToolResponse."""
    content = policy.content or {}
    return ToolResponse(
        id=policy.id,
        school_id=policy.school_id,
        tool_name=content.get("tool_name", ""),
        vendor=content.get("vendor", ""),
        risk_level=content.get("risk_level", ""),
        approval_status=content.get("approval_status", ""),
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _audit_to_response(audit: GovernanceAudit) -> AuditResponse:
    """Convert audit model to response schema."""
    return AuditResponse(
        id=audit.id,
        policy_id=audit.policy_id,
        action=audit.action,
        actor_id=audit.actor_id,
        diff=audit.diff,
        timestamp=audit.timestamp,
    )
