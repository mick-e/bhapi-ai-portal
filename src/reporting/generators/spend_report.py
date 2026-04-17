"""Spend report generator — by member and provider breakdown."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.billing import LLMAccount, SpendRecord
from src.groups import GroupMember
from src.reporting.generators.base import BaseGenerator


class SpendReportGenerator(BaseGenerator):
    report_type = "spend"
    title = "Spend Report"

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
                SpendRecord.id,
                SpendRecord.amount,
                SpendRecord.currency,
                SpendRecord.token_count,
                SpendRecord.model,
                SpendRecord.period_start,
                LLMAccount.provider,
                GroupMember.display_name.label("member_name"),
            )
            .outerjoin(LLMAccount, SpendRecord.llm_account_id == LLMAccount.id)
            .outerjoin(GroupMember, SpendRecord.member_id == GroupMember.id)
            .where(
                SpendRecord.group_id == self.group_id,
                SpendRecord.period_start >= period_start,
                SpendRecord.period_start <= period_end,
            )
            .order_by(SpendRecord.period_start.desc())
        )
        rows = result.all()

        return [
            {
                "id": str(r.id),
                "date": r.period_start.strftime("%Y-%m-%d") if r.period_start else "",
                "provider": r.provider or "Unknown",
                "model": r.model or "-",
                "member_name": r.member_name or "-",
                "amount": f"${r.amount:.2f}",
                "currency": r.currency,
                "tokens": str(r.token_count) if r.token_count else "-",
            }
            for r in rows
        ]

    def get_columns(self) -> list[str]:
        return ["Date", "Provider", "Model", "Member", "Amount", "Tokens"]

    def row_to_values(self, row: dict) -> list[str]:
        return [
            row["date"],
            row["provider"],
            row["model"],
            row["member_name"],
            row["amount"],
            row["tokens"],
        ]
