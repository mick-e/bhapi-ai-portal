"""E2E tests for legal document endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def legal_client():
    """Test client for legal endpoints (no auth needed)."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_privacy_policy_returns_200(legal_client):
    """GET /legal/privacy returns 200 with HTML content."""
    resp = await legal_client.get("/legal/privacy")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Privacy Policy" in resp.text


@pytest.mark.asyncio
async def test_privacy_policy_contains_required_sections(legal_client):
    """Privacy policy includes all required GDPR sections."""
    resp = await legal_client.get("/legal/privacy")
    text = resp.text
    assert "Data Controller" in text
    assert "Data We Collect" in text
    assert "Lawful Basis" in text
    assert "Data Minimisation" in text
    assert "Data Retention" in text
    assert "Your Rights" in text
    assert "Children" in text
    assert "International Transfers" in text
    assert "Third Parties" in text
    assert "Cookies" in text
    assert "dpo@bhapi.ai" in text


@pytest.mark.asyncio
async def test_terms_of_service_returns_200(legal_client):
    """GET /legal/terms returns 200 with HTML content."""
    resp = await legal_client.get("/legal/terms")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Terms of Service" in resp.text


@pytest.mark.asyncio
async def test_terms_of_service_contains_required_sections(legal_client):
    """Terms of service includes all required sections."""
    resp = await legal_client.get("/legal/terms")
    text = resp.text
    assert "Service Description" in text
    assert "Eligibility" in text
    assert "Acceptable Use" in text
    assert "Prohibited Uses" in text
    assert "Subscription and Billing" in text
    assert "Refund Policy" in text
    assert "Intellectual Property" in text
    assert "Limitation of Liability" in text
    assert "Termination" in text
    assert "Governing Law" in text
    assert "Dispute Resolution" in text


@pytest.mark.asyncio
async def test_legal_pages_require_no_auth(legal_client):
    """Legal pages are accessible without authentication."""
    # No auth headers — should still return 200
    privacy = await legal_client.get("/legal/privacy")
    assert privacy.status_code == 200

    terms = await legal_client.get("/legal/terms")
    assert terms.status_code == 200
