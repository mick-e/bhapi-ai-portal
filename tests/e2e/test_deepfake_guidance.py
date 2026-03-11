"""E2E tests for the deepfake guidance endpoint."""

import pytest

from src.risk.deepfake_guidance import DEEPFAKE_GUIDANCE, get_deepfake_guidance


@pytest.mark.asyncio
async def test_get_deepfake_guidance_returns_content():
    """get_deepfake_guidance returns the full guidance dict."""
    result = await get_deepfake_guidance()
    assert "what_is_deepfake" in result
    assert isinstance(result["what_is_deepfake"], str)
    assert len(result["what_is_deepfake"]) > 0


@pytest.mark.asyncio
async def test_guidance_has_reporting_resources():
    """Guidance includes at least NCMEC and FBI."""
    result = await get_deepfake_guidance()
    resources = result["reporting_resources"]
    assert len(resources) >= 3
    names = [r["name"] for r in resources]
    assert "NCMEC CyberTipline" in names
    assert "FBI IC3" in names
    assert "TAKE IT DOWN" in names


@pytest.mark.asyncio
async def test_guidance_has_parent_actions():
    """Guidance includes parent action steps."""
    result = await get_deepfake_guidance()
    actions = result["parent_actions"]
    assert len(actions) >= 4


@pytest.mark.asyncio
async def test_guidance_has_prevention_tips():
    """Guidance includes prevention tips."""
    result = await get_deepfake_guidance()
    tips = result["prevention_tips"]
    assert len(tips) >= 3


@pytest.mark.asyncio
async def test_guidance_resources_have_urls():
    """Each reporting resource has a valid URL."""
    result = await get_deepfake_guidance()
    for resource in result["reporting_resources"]:
        assert "url" in resource
        assert resource["url"].startswith("https://")
        assert "name" in resource


@pytest.mark.asyncio
async def test_deepfake_guidance_endpoint_public(client):
    """GET /api/v1/risk/deepfake-guidance is accessible without auth."""
    resp = await client.get("/api/v1/risk/deepfake-guidance")
    assert resp.status_code == 200
    data = resp.json()
    assert "what_is_deepfake" in data
    assert "reporting_resources" in data
    assert "parent_actions" in data
    assert "prevention_tips" in data


@pytest.mark.asyncio
async def test_deepfake_guidance_constant_matches_function():
    """The module constant and function return the same content."""
    result = await get_deepfake_guidance()
    assert result == DEEPFAKE_GUIDANCE
