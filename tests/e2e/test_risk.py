"""E2E tests for the platform safety ratings endpoint."""

import pytest


EXPECTED_PLATFORMS = [
    "ChatGPT",
    "Gemini",
    "Copilot",
    "Claude",
    "Grok",
    "Character.AI",
    "Replika",
    "Pi",
    "Perplexity",
    "Poe",
]

REQUIRED_FIELDS = [
    "platform",
    "safety_score",
    "risk_level",
    "categories_of_concern",
    "last_updated",
]


@pytest.mark.asyncio
async def test_platform_ratings_returns_200(client):
    """GET /api/v1/risk/platform-ratings returns 200."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_platform_ratings_has_all_platforms(client):
    """Response contains all 10 monitored AI platforms."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()
    assert "platforms" in data
    assert len(data["platforms"]) == 10

    returned_names = [p["platform"] for p in data["platforms"]]
    for name in EXPECTED_PLATFORMS:
        assert name in returned_names, f"Missing platform: {name}"


@pytest.mark.asyncio
async def test_platform_ratings_required_fields(client):
    """Each platform rating has all required fields."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    for platform in data["platforms"]:
        for field in REQUIRED_FIELDS:
            assert field in platform, (
                f"Missing field '{field}' in platform '{platform.get('platform')}'"
            )


@pytest.mark.asyncio
async def test_platform_ratings_score_range(client):
    """Safety scores are within 0-100 range."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    for platform in data["platforms"]:
        score = platform["safety_score"]
        assert 0 <= score <= 100, (
            f"{platform['platform']} score {score} out of range"
        )


@pytest.mark.asyncio
async def test_platform_ratings_risk_levels(client):
    """Risk levels are one of low/medium/high."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    valid_levels = {"low", "medium", "high"}
    for platform in data["platforms"]:
        assert platform["risk_level"] in valid_levels, (
            f"{platform['platform']} has invalid risk_level: {platform['risk_level']}"
        )


@pytest.mark.asyncio
async def test_platform_ratings_categories_non_empty(client):
    """Each platform has at least one category of concern."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    for platform in data["platforms"]:
        assert isinstance(platform["categories_of_concern"], list)
        assert len(platform["categories_of_concern"]) >= 1, (
            f"{platform['platform']} has no categories of concern"
        )


@pytest.mark.asyncio
async def test_platform_ratings_no_auth_required(client):
    """Endpoint is accessible without authentication headers."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_platform_ratings_high_risk_platforms(client):
    """Character.AI, Replika, and Grok should be high risk."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    high_risk = {
        p["platform"] for p in data["platforms"] if p["risk_level"] == "high"
    }
    assert "Character.AI" in high_risk
    assert "Replika" in high_risk
    assert "Grok" in high_risk


@pytest.mark.asyncio
async def test_platform_ratings_claude_is_safest(client):
    """Claude should have the highest safety score due to Constitutional AI."""
    resp = await client.get("/api/v1/risk/platform-ratings")
    data = resp.json()

    scores = {p["platform"]: p["safety_score"] for p in data["platforms"]}
    assert scores["Claude"] == max(scores.values())
