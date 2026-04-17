"""Activity report generator — AI usage summary by member and platform."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.capture import CaptureEvent
from src.groups import GroupMember
from src.reporting.generators.base import BaseGenerator


class ActivityReportGenerator(BaseGenerator):
    report_type = "activity"
    title = "Activity Report"

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

        result = await self.db.execute(
            select(
                CaptureEvent.id,
                CaptureEvent.platform,
                CaptureEvent.event_type,
                CaptureEvent.timestamp,
                CaptureEvent.source_channel,
                GroupMember.display_name.label("member_name"),
            )
            .outerjoin(GroupMember, CaptureEvent.member_id == GroupMember.id)
            .where(
                CaptureEvent.group_id == self.group_id,
                CaptureEvent.timestamp >= period_start,
                CaptureEvent.timestamp <= period_end,
            )
            .order_by(CaptureEvent.timestamp.desc())
        )
        rows = result.all()

        return [
            {
                "id": str(r.id),
                "member_name": r.member_name or "Unknown",
                "platform": r.platform,
                "event_type": r.event_type,
                "source": r.source_channel,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "",
            }
            for r in rows
        ]

    def get_columns(self) -> list[str]:
        return ["Date/Time", "Member", "Platform", "Event Type", "Source"]

    def row_to_values(self, row: dict) -> list[str]:
        return [
            row["timestamp"],
            row["member_name"],
            row["platform"],
            row["event_type"],
            row["source"],
        ]
