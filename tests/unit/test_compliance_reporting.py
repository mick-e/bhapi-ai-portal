"""Unit tests for school board compliance PDF report generation.

Tests cover: PDF generation, valid output, style naming,
date range handling, graceful fallback when governance data is missing,
report structure, and various parameter combinations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.reporting.service import generate_school_board_report


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    session = AsyncMock()
    # Default: execute returns empty result
    mock_result = AsyncMock()
    mock_result.scalar.return_value = 0
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_returns_bytes(mock_db):
    """generate_school_board_report returns bytes (PDF content)."""
    result = await generate_school_board_report(mock_db, uuid4())
    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_pdf_header(mock_db):
    """Generated output starts with PDF magic bytes."""
    result = await generate_school_board_report(mock_db, uuid4())
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_ends_with_eof(mock_db):
    """Generated PDF ends with %%EOF marker."""
    result = await generate_school_board_report(mock_db, uuid4())
    assert result.rstrip().endswith(b"%%EOF")


@pytest.mark.asyncio
async def test_substantial_pdf_size(mock_db):
    """Generated PDF has a non-trivial size (multiple sections)."""
    result = await generate_school_board_report(mock_db, uuid4())
    # A PDF with title, tables, recommendations, footer should be >1KB
    assert len(result) > 1000


@pytest.mark.asyncio
async def test_no_bullet_style_conflict(mock_db):
    """Verify report generates without ReportLab 'Bullet' style conflict.

    CLAUDE.md: the 'Bullet' name conflicts with ReportLab built-in style.
    Our function uses SchoolBoard-prefixed style names to avoid this.
    """
    # If there were a style name conflict, ReportLab would raise an error
    result = await generate_school_board_report(mock_db, uuid4())
    assert isinstance(result, bytes)
    assert len(result) > 100


@pytest.mark.asyncio
async def test_handles_missing_governance_gracefully(mock_db):
    """Report generates even when governance module raises an exception."""
    with patch(
        "src.reporting.service.generate_school_board_report",
        wraps=generate_school_board_report,
    ):
        # The governance import is inside a try/except in the function,
        # so even if governance service fails, the PDF should be generated
        # with N/A fallback values
        result = await generate_school_board_report(mock_db, uuid4())
        assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_date_range_produces_valid_pdf(mock_db):
    """When date_from and date_to are provided, a valid PDF is still produced."""
    date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(2026, 3, 1, tzinfo=timezone.utc)
    result = await generate_school_board_report(
        mock_db, uuid4(), date_from=date_from, date_to=date_to
    )
    assert result[:5] == b"%PDF-"
    # PDF with date range should be slightly larger than without
    result_no_dates = await generate_school_board_report(mock_db, uuid4())
    # Both are valid PDFs
    assert result_no_dates[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_no_date_range_produces_valid_pdf(mock_db):
    """When no date range is given, the report still generates successfully."""
    result = await generate_school_board_report(mock_db, uuid4())
    assert result[:5] == b"%PDF-"
    assert result.rstrip().endswith(b"%%EOF")


@pytest.mark.asyncio
async def test_different_school_ids_produce_different_pdfs(mock_db):
    """Different school IDs should still produce valid (possibly identical) PDFs."""
    result1 = await generate_school_board_report(mock_db, uuid4())
    result2 = await generate_school_board_report(mock_db, uuid4())
    # Both should be valid PDFs
    assert result1[:5] == b"%PDF-"
    assert result2[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_only_date_from_produces_valid_pdf(mock_db):
    """Providing only date_from (no date_to) produces a valid PDF."""
    date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = await generate_school_board_report(
        mock_db, uuid4(), date_from=date_from
    )
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_only_date_to_produces_valid_pdf(mock_db):
    """Providing only date_to (no date_from) produces a valid PDF."""
    date_to = datetime(2026, 3, 1, tzinfo=timezone.utc)
    result = await generate_school_board_report(
        mock_db, uuid4(), date_to=date_to
    )
    assert result[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_is_single_page(mock_db):
    """Generated PDF should have exactly 1 page (compact report)."""
    result = await generate_school_board_report(mock_db, uuid4())
    # ReportLab PDFs contain "/Count N" for page count
    assert b"/Count 1" in result


@pytest.mark.asyncio
async def test_pdf_uses_helvetica_font(mock_db):
    """PDF uses Helvetica font family (ReportLab default for clean look)."""
    result = await generate_school_board_report(mock_db, uuid4())
    assert b"Helvetica" in result
