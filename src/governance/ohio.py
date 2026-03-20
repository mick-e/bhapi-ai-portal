"""Ohio governance extensions — district customization, CSV import, board reports.

Provides Ohio-specific governance features:
- District customization of Ohio policy templates
- Bulk CSV import of AI tools
- Board-ready compliance report generation
- Ohio compliance status check
"""

import csv
import io
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.governance.models import GovernanceAudit, GovernanceImportLog, GovernancePolicy
from src.governance.service import (
    REQUIRED_POLICY_TYPES,
    _policy_to_response,
    _tool_to_response,
    add_tool_to_inventory,
    run_risk_assessment,
)

logger = structlog.get_logger()

# Ohio-mandated policy types
OHIO_REQUIRED_POLICY_TYPES = [
    "ai_usage",
    "tool_inventory",
    "risk_assessment",
    "governance",
]


async def customize_ohio_policy(
    db: AsyncSession,
    school_id: str | UUID,
    district_name: str,
    additional_requirements: list[str] | None = None,
    approved_tools: list[str] | None = None,
    actor_id: UUID | None = None,
) -> dict:
    """Customize the Ohio policy template with district-specific requirements.

    Creates or updates an Ohio governance policy with district name,
    additional local requirements, and pre-approved tools.
    """
    if isinstance(school_id, str):
        school_id = UUID(school_id)

    if not district_name or not district_name.strip():
        raise ValidationError("district_name is required")

    additional_requirements = additional_requirements or []
    approved_tools = approved_tools or []

    # Build the customized content
    content = {
        "district_name": district_name,
        "state_code": "OH",
        "additional_requirements": additional_requirements,
        "approved_tools": [
            {"name": t, "approved_date": datetime.now(timezone.utc).isoformat()}
            for t in approved_tools
        ],
        "base_template": "ohio_ai_usage",
        "customized_at": datetime.now(timezone.utc).isoformat(),
    }

    # Build district customizations dict
    district_customizations = {
        "additional_requirements": additional_requirements,
        "approved_tools": approved_tools,
    }

    # Create the policy
    policy = GovernancePolicy(
        id=uuid4(),
        school_id=school_id,
        state_code="OH",
        policy_type="ai_usage",
        content=content,
        status="active",
        version=1,
        district_name=district_name,
        district_customizations=district_customizations,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)

    # Audit trail
    if actor_id:
        audit = GovernanceAudit(
            id=uuid4(),
            policy_id=policy.id,
            action="ohio_customized",
            actor_id=actor_id,
            diff={"district_name": district_name, "customizations": district_customizations},
        )
        db.add(audit)
        await db.flush()

    logger.info(
        "ohio_policy_customized",
        school_id=str(school_id),
        district_name=district_name,
        tool_count=len(approved_tools),
    )

    return {
        "state_code": "OH",
        "policy_id": str(policy.id),
        "content": content,
        "status": policy.status,
        "version": policy.version,
    }


async def import_tools_csv(
    db: AsyncSession,
    school_id: str | UUID,
    csv_data: str,
    actor_id: UUID | None = None,
) -> dict:
    """Parse and import AI tools from CSV data.

    Expected CSV columns: tool_name, vendor, risk_level, approval_status
    Returns summary with imported count and any errors.
    """
    if isinstance(school_id, str):
        school_id = UUID(school_id)

    errors: list[dict] = []
    imported = 0
    rows_parsed = 0

    try:
        reader = csv.DictReader(io.StringIO(csv_data.strip()))
    except Exception as exc:
        raise ValidationError(f"Invalid CSV data: {exc}") from exc

    required_fields = {"tool_name", "vendor", "risk_level", "approval_status"}
    if reader.fieldnames:
        missing = required_fields - set(reader.fieldnames)
        if missing:
            raise ValidationError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    valid_risk_levels = {"low", "medium", "high"}
    valid_approval_statuses = {"pending", "approved", "denied"}

    for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        rows_parsed += 1
        tool_name = (row.get("tool_name") or "").strip()
        vendor = (row.get("vendor") or "").strip()
        risk_level = (row.get("risk_level") or "").strip().lower()
        approval_status = (row.get("approval_status") or "").strip().lower()

        # Validate
        row_errors = []
        if not tool_name:
            row_errors.append("tool_name is required")
        if not vendor:
            row_errors.append("vendor is required")
        if risk_level not in valid_risk_levels:
            row_errors.append(f"risk_level must be one of: {', '.join(sorted(valid_risk_levels))}")
        if approval_status not in valid_approval_statuses:
            row_errors.append(
                f"approval_status must be one of: {', '.join(sorted(valid_approval_statuses))}"
            )

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors, "data": dict(row)})
            continue

        # Create tool entry (stored as governance policy with type=tool_inventory)
        content = {
            "tool_name": tool_name,
            "vendor": vendor,
            "risk_level": risk_level,
            "approval_status": approval_status,
        }
        policy = GovernancePolicy(
            id=uuid4(),
            school_id=school_id,
            state_code="OH",
            policy_type="tool_inventory",
            content=content,
            status="active",
            version=1,
        )
        db.add(policy)
        imported += 1

    await db.flush()

    # Log the import
    import_log = GovernanceImportLog(
        id=uuid4(),
        school_id=school_id,
        actor_id=actor_id or uuid4(),
        import_type="csv",
        total_rows=rows_parsed,
        imported_count=imported,
        error_count=len(errors),
        errors=errors if errors else None,
    )
    db.add(import_log)
    await db.flush()

    logger.info(
        "ohio_tools_imported",
        school_id=str(school_id),
        imported=imported,
        errors=len(errors),
        total_rows=rows_parsed,
    )

    return {
        "imported": imported,
        "errors": errors,
        "total_rows": rows_parsed,
        "import_log_id": str(import_log.id),
    }


async def generate_board_report(
    db: AsyncSession,
    school_id: str | UUID,
) -> dict:
    """Generate a board-ready compliance report.

    Aggregates policy coverage, tool inventory, risk assessment,
    and audit trail data into a PDF-ready structure.
    """
    if isinstance(school_id, str):
        school_id = UUID(school_id)

    # Get all non-archived policies (excluding tool_inventory)
    policies_result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type != "tool_inventory",
            GovernancePolicy.status != "archived",
        )
    )
    policies = list(policies_result.scalars().all())
    policy_types = {p.policy_type for p in policies}

    # Get tools
    tools_result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type == "tool_inventory",
        )
    )
    tools = list(tools_result.scalars().all())

    # Get risk assessment
    risk = await run_risk_assessment(db, school_id)

    # Get recent audits
    audit_result = await db.execute(
        select(GovernanceAudit)
        .join(GovernancePolicy, GovernanceAudit.policy_id == GovernancePolicy.id)
        .where(GovernancePolicy.school_id == school_id)
        .order_by(GovernanceAudit.timestamp.desc())
        .limit(50)
    )
    audits = list(audit_result.scalars().all())

    # Categorize tools by risk level
    tools_by_risk = {"low": 0, "medium": 0, "high": 0}
    tools_by_status = {"pending": 0, "approved": 0, "denied": 0}
    for tool in tools:
        content = tool.content or {}
        rl = content.get("risk_level", "")
        st = content.get("approval_status", "")
        if rl in tools_by_risk:
            tools_by_risk[rl] += 1
        if st in tools_by_status:
            tools_by_status[st] += 1

    # Compliance gaps
    missing_policies = [t for t in OHIO_REQUIRED_POLICY_TYPES if t not in policy_types and t != "tool_inventory"]
    is_compliant = len(missing_policies) == 0 and risk.score >= 70

    # Get district name from any policy
    district_name = None
    for p in policies:
        if p.district_name:
            district_name = p.district_name
            break

    report = {
        "format": "pdf",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_code": "OH",
        "district_name": district_name,
        "compliance_score": risk.score,
        "is_compliant": is_compliant,
        "tool_inventory_count": len(tools),
        "tools_by_risk": tools_by_risk,
        "tools_by_status": tools_by_status,
        "policy_count": len(policies),
        "policy_coverage": list(policy_types),
        "missing_policies": missing_policies,
        "risk_findings": [
            {"description": f.description, "deduction": f.deduction}
            for f in risk.findings
        ],
        "audit_count": len(audits),
        "recent_actions": [
            {"action": a.action, "timestamp": a.timestamp.isoformat() if a.timestamp else None}
            for a in audits[:10]
        ],
    }

    logger.info(
        "ohio_board_report_generated",
        school_id=str(school_id),
        compliance_score=risk.score,
        tool_count=len(tools),
    )

    return report


async def get_ohio_compliance_status(
    db: AsyncSession,
    school_id: str | UUID,
) -> dict:
    """Check all required Ohio policies exist and are active.

    Returns detailed status for each required policy type and overall
    compliance readiness.
    """
    if isinstance(school_id, str):
        school_id = UUID(school_id)

    # Get all non-archived policies
    policies_result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.school_id == school_id,
            GovernancePolicy.policy_type != "tool_inventory",
            GovernancePolicy.status != "archived",
        )
    )
    policies = list(policies_result.scalars().all())
    policy_types = {p.policy_type for p in policies}

    # Active policy count
    active_count = sum(1 for p in policies if p.status == "active")

    # Get tool count
    tools_result = await db.execute(
        select(func.count()).select_from(
            select(GovernancePolicy).where(
                GovernancePolicy.school_id == school_id,
                GovernancePolicy.policy_type == "tool_inventory",
            ).subquery()
        )
    )
    tool_count = tools_result.scalar() or 0

    # Check each required type
    required_types_except_inventory = [
        t for t in OHIO_REQUIRED_POLICY_TYPES if t != "tool_inventory"
    ]
    status_items = {}
    for req_type in required_types_except_inventory:
        if req_type in policy_types:
            # Check if at least one is active
            active_for_type = any(
                p.policy_type == req_type and p.status == "active"
                for p in policies
            )
            status_items[req_type] = {
                "exists": True,
                "active": active_for_type,
                "status": "compliant" if active_for_type else "draft_only",
            }
        else:
            status_items[req_type] = {
                "exists": False,
                "active": False,
                "status": "missing",
            }

    # Tool inventory check: at least one tool must exist
    has_tools = tool_count > 0
    status_items["tool_inventory"] = {
        "exists": has_tools,
        "active": has_tools,
        "status": "compliant" if has_tools else "missing",
    }

    all_compliant = all(
        item["status"] == "compliant" for item in status_items.values()
    )

    # Overall deadline
    compliance_deadline = "2026-07-01"

    return {
        "school_id": str(school_id),
        "state_code": "OH",
        "overall_status": "compliant" if all_compliant else "non_compliant",
        "compliance_deadline": compliance_deadline,
        "policy_status": status_items,
        "active_policy_count": active_count,
        "tool_count": tool_count,
        "ready_for_board": all_compliant,
    }
