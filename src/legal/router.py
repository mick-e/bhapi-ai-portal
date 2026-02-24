"""Legal document endpoints — public, no auth required."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.legal.content import PRIVACY_POLICY, TERMS_OF_SERVICE

router = APIRouter()


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Serve the privacy policy."""
    return HTMLResponse(content=PRIVACY_POLICY)


@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Serve the terms of service."""
    return HTMLResponse(content=TERMS_OF_SERVICE)
