"""E2E tests for AI Platform Safety Ratings."""


import pytest


@pytest.mark.asyncio
async def test_get_all_platform_safety_public(client):
    """Platform safety endpoint should be public (no auth)."""
    resp = await client.get("/api/v1/billing/platform-safety")
    assert resp.status_code == 200
    data = resp.json()
    assert "platforms" in data
    assert len(data["platforms"]) == 8


@pytest.mark.asyncio
async def test_get_all_platforms_have_required_fields(client):
    """All platforms should have required fields."""
    resp = await client.get("/api/v1/billing/platform-safety")
    data = resp.json()

    for platform in data["platforms"]:
        assert "key" in platform
        assert "name" in platform
        assert "overall_grade" in platform
        assert platform["overall_grade"] in ("A", "B", "C", "D", "F")
        assert "min_age_recommended" in platform
        assert "has_parental_controls" in platform
        assert "has_content_filters" in platform
        assert "data_retention_days" in platform
        assert "coppa_compliant" in platform
        assert "known_incidents" in platform
        assert isinstance(platform["strengths"], list)
        assert isinstance(platform["concerns"], list)
        assert "last_updated" in platform


@pytest.mark.asyncio
async def test_get_single_platform_safety(client):
    """Single platform endpoint should return correct data."""
    resp = await client.get("/api/v1/billing/platform-safety/chatgpt")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "chatgpt"
    assert data["name"] == "ChatGPT (OpenAI)"
    assert data["overall_grade"] == "B"


@pytest.mark.asyncio
async def test_get_single_platform_not_found(client):
    """Unknown platform should return 404."""
    resp = await client.get("/api/v1/billing/platform-safety/unknown_platform")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_platform_safety_recommend_by_age(client):
    """Age-filtered recommendations should include recommendation field."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=12")
    assert resp.status_code == 200
    data = resp.json()
    assert "platforms" in data

    for platform in data["platforms"]:
        assert "recommendation" in platform
        assert platform["recommendation"] in (
            "recommended",
            "use_with_caution",
            "not_recommended",
        )


@pytest.mark.asyncio
async def test_platform_safety_recommend_young_child(client):
    """Very young child (age 8) should see most platforms as not recommended."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=8")
    data = resp.json()

    not_recommended = [
        p for p in data["platforms"] if p["recommendation"] == "not_recommended"
    ]
    # Grok and Replika require 18+, CharacterAI requires 16+
    assert len(not_recommended) >= 3


@pytest.mark.asyncio
async def test_platform_safety_recommend_teen(client):
    """Teenager (age 15) should have some recommended platforms."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=15")
    data = resp.json()

    recommended = [
        p for p in data["platforms"] if p["recommendation"] == "recommended"
    ]
    # Platforms with min_age 13 should be recommended for 15-year-olds
    assert len(recommended) >= 4


@pytest.mark.asyncio
async def test_platform_safety_recommend_adult(client):
    """Adult (age 25) should see all platforms recommended."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=25")
    data = resp.json()

    recommended = [
        p for p in data["platforms"] if p["recommendation"] == "recommended"
    ]
    assert len(recommended) == 8


@pytest.mark.asyncio
async def test_platform_safety_recommend_invalid_age(client):
    """Invalid age should return 422."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=0")
    assert resp.status_code == 422

    resp = await client.get("/api/v1/billing/platform-safety/recommend?age=101")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_platform_safety_recommend_missing_age(client):
    """Missing age parameter should return 422."""
    resp = await client.get("/api/v1/billing/platform-safety/recommend")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_platform_safety_public_no_auth_header(client):
    """Platform safety endpoints should not require auth headers."""
    # All three endpoints should work without any auth
    resp1 = await client.get("/api/v1/billing/platform-safety")
    assert resp1.status_code == 200

    resp2 = await client.get("/api/v1/billing/platform-safety/claude")
    assert resp2.status_code == 200

    resp3 = await client.get("/api/v1/billing/platform-safety/recommend?age=14")
    assert resp3.status_code == 200


@pytest.mark.asyncio
async def test_claude_is_grade_a(client):
    """Claude should have the highest safety grade."""
    resp = await client.get("/api/v1/billing/platform-safety/claude")
    data = resp.json()
    assert data["overall_grade"] == "A"


@pytest.mark.asyncio
async def test_grok_is_low_grade(client):
    """Grok should have a low safety grade due to safety concerns."""
    resp = await client.get("/api/v1/billing/platform-safety/grok")
    data = resp.json()
    assert data["overall_grade"] in ("D", "F")
    assert data["min_age_recommended"] == 18
