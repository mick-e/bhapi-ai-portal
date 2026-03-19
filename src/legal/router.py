"""Legal document endpoints — public, no auth required."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from src.legal.content import PRIVACY_FOR_CHILDREN, PRIVACY_POLICY, TERMS_OF_SERVICE

router = APIRouter()


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Serve the privacy policy."""
    return HTMLResponse(content=PRIVACY_POLICY)


@router.get("/privacy-for-children", response_class=HTMLResponse)
async def privacy_for_children():
    """Serve the child-friendly privacy notice (COPPA 2026 compliance)."""
    return HTMLResponse(content=PRIVACY_FOR_CHILDREN)


@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Serve the terms of service."""
    return HTMLResponse(content=TERMS_OF_SERVICE)


@router.get("/security-program")
async def security_program():
    """Serve the COPPA-formatted written information security program."""
    doc_path = Path(__file__).resolve().parent.parent.parent / "docs" / "compliance" / "security-program.md"
    if doc_path.is_file():
        content = doc_path.read_text(encoding="utf-8")
        return PlainTextResponse(content=content, media_type="text/markdown")
    return PlainTextResponse(content="Security program document not found.", status_code=404)
