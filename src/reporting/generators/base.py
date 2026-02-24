"""Abstract base report generator."""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession


class BaseGenerator(ABC):
    """Base class for all report generators."""

    report_type: str = ""
    title: str = ""

    def __init__(self, db: AsyncSession, group_id: UUID):
        self.db = db
        self.group_id = group_id

    @abstractmethod
    async def fetch_data(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> list[dict]:
        """Fetch report data from the database."""

    @abstractmethod
    def get_columns(self) -> list[str]:
        """Return column headers for the report."""

    @abstractmethod
    def row_to_values(self, row: dict) -> list[str]:
        """Convert a data row to a list of display values."""

    async def generate_pdf(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> bytes:
        """Generate a PDF report."""
        data = await self.fetch_data(period_start, period_end)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        # Use unique style names to avoid ReportLab "Bullet" conflict
        title_style = ParagraphStyle(
            f"BhapiTitle_{self.report_type}",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=12,
        )
        subtitle_style = ParagraphStyle(
            f"BhapiSubtitle_{self.report_type}",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=20,
        )

        elements: list = []

        # Title
        elements.append(Paragraph(self.title, title_style))

        # Period info
        now = datetime.now(timezone.utc)
        start_str = period_start.strftime("%Y-%m-%d") if period_start else "N/A"
        end_str = period_end.strftime("%Y-%m-%d") if period_end else now.strftime("%Y-%m-%d")
        elements.append(
            Paragraph(f"Period: {start_str} to {end_str} | Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}", subtitle_style)
        )
        elements.append(Spacer(1, 10))

        if not data:
            elements.append(Paragraph("No data found for the selected period.", styles["Normal"]))
        else:
            # Build table
            columns = self.get_columns()
            table_data = [columns]
            for row in data:
                table_data.append(self.row_to_values(row))

            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(table)

        # Footer
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            f"BhapiFooter_{self.report_type}",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
        )
        elements.append(
            Paragraph(f"bhapi.ai — AI Safety Report | {len(data)} records", footer_style)
        )

        doc.build(elements)
        return buf.getvalue()

    async def generate_csv(
        self,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> bytes:
        """Generate a CSV report."""
        data = await self.fetch_data(period_start, period_end)
        buf = io.StringIO()
        columns = self.get_columns()
        writer = csv.writer(buf)
        writer.writerow(columns)
        for row in data:
            writer.writerow(self.row_to_values(row))
        return buf.getvalue().encode("utf-8")

    async def generate(
        self,
        fmt: str = "pdf",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> bytes:
        """Generate report in the requested format."""
        if fmt == "csv":
            return await self.generate_csv(period_start, period_end)
        elif fmt == "json":
            import json
            data = await self.fetch_data(period_start, period_end)
            return json.dumps(data, default=str, indent=2).encode("utf-8")
        else:
            return await self.generate_pdf(period_start, period_end)
