"""Compliance report generator — safeguarding summary for governance."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.models import AuditEntry, ConsentRecord
from src.groups.models import GroupMember
from src.reporting.generators.base import BaseGenerator


class ComplianceReportGenerator(BaseGenerator):
    report_type = "compliance"
    title = "Compliance & Safeguarding Report"

    async def fetch_data(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        if not period_start:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not period_end:
            period_end = now

        # Fetch consent records
        consent_result = await self.db.execute(
            select(
                ConsentRecord.id,
                ConsentRecord.consent_type,
                ConsentRecord.given_at,
                ConsentRecord.withdrawn_at,
                GroupMember.display_name.label("member_name"),
            )
            .outerjoin(GroupMember, ConsentRecord.member_id == GroupMember.id)
            .where(
                ConsentRecord.group_id == self.group_id,
                ConsentRecord.created_at >= period_start,
                ConsentRecord.created_at <= period_end,
            )
            .order_by(ConsentRecord.created_at.desc())
        )
        consent_rows = consent_result.all()

        # Fetch audit entries
        audit_result = await self.db.execute(
            select(
                AuditEntry.id,
                AuditEntry.action,
                AuditEntry.resource_type,
                AuditEntry.created_at,
            )
            .where(
                AuditEntry.group_id == self.group_id,
                AuditEntry.created_at >= period_start,
                AuditEntry.created_at <= period_end,
            )
            .order_by(AuditEntry.created_at.desc())
        )
        audit_rows = audit_result.all()

        rows: list[dict] = []

        for c in consent_rows:
            status = "Withdrawn" if c.withdrawn_at else "Active"
            rows.append({
                "id": str(c.id),
                "date": c.given_at.strftime("%Y-%m-%d %H:%M") if c.given_at else "",
                "type": "Consent",
                "detail": c.consent_type,
                "member_name": c.member_name or "Unknown",
                "status": status,
            })

        for a in audit_rows:
            rows.append({
                "id": str(a.id),
                "date": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                "type": "Audit",
                "detail": a.action,
                "member_name": a.resource_type,
                "status": "-",
            })

        # Sort combined results by date descending
        rows.sort(key=lambda r: r["date"], reverse=True)
        return rows

    def get_columns(self) -> list[str]:
        return ["Date", "Record Type", "Detail", "Member/Resource", "Status"]

    def row_to_values(self, row: dict) -> list[str]:
        return [
            row["date"],
            row["type"],
            row["detail"],
            row["member_name"],
            row["status"],
        ]
