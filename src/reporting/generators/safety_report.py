"""Safety (risk) report generator — risk events table with severity breakdown."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.groups.models import GroupMember
from src.reporting.generators.base import BaseGenerator
from src.risk.models import RiskEvent


class SafetyReportGenerator(BaseGenerator):
    report_type = "risk"
    title = "Safety Report"

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

        # Fetch risk events with member names
        result = await self.db.execute(
            select(
                RiskEvent.id,
                RiskEvent.category,
                RiskEvent.severity,
                RiskEvent.confidence,
                RiskEvent.acknowledged,
                RiskEvent.created_at,
                GroupMember.display_name.label("member_name"),
            )
            .outerjoin(GroupMember, RiskEvent.member_id == GroupMember.id)
            .where(
                RiskEvent.group_id == self.group_id,
                RiskEvent.created_at >= period_start,
                RiskEvent.created_at <= period_end,
            )
            .order_by(RiskEvent.created_at.desc())
        )
        rows = result.all()

        return [
            {
                "id": str(r.id),
                "member_name": r.member_name or "Unknown",
                "category": r.category,
                "severity": r.severity,
                "confidence": round(r.confidence, 2) if r.confidence else 0,
                "acknowledged": "Yes" if r.acknowledged else "No",
                "date": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in rows
        ]

    def get_columns(self) -> list[str]:
        return ["Date", "Member", "Category", "Severity", "Confidence", "Acknowledged"]

    def row_to_values(self, row: dict) -> list[str]:
        return [
            row["date"],
            row["member_name"],
            row["category"],
            row["severity"],
            str(row["confidence"]),
            row["acknowledged"],
        ]
