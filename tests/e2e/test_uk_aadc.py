"""E2E tests for UK AADC compliance endpoints.

Tests the full HTTP request/response cycle for AADC gap analysis,
privacy-by-default settings, and assessment history endpoints.
"""

from uuid import uuid4

import pytest

from src.compliance.uk_aadc import (
    apply_privacy_defaults,
    get_assessment_history,
    get_default_privacy_settings,
    get_latest_assessment,
    get_privacy_defaults_for_user,
    run_gap_analysis,
)
from src.exceptions import NotFoundError, ValidationError
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_e2e_run_gap_analysis_and_retrieve(test_session):
    """Full flow: run gap analysis, then retrieve it."""
    group, owner_id = await make_test_group(test_session, name="AADC E2E", group_type="family")

    # Run analysis
    result = await run_gap_analysis(test_session, group.id, assessor="e2e-tester")
    assert result["group_id"] == str(group.id)
    assert len(result["standards"]) == 15
    assert result["assessor"] == "e2e-tester"

    # Retrieve latest
    latest = await get_latest_assessment(test_session, group.id)
    assert latest is not None
    assert latest["id"] == result["id"]
    assert latest["assessor"] == "e2e-tester"


@pytest.mark.asyncio
async def test_e2e_gap_analysis_compliant_group(test_session):
    """Fully compliant group should score 100."""
    group, owner_id = await make_test_group(
        test_session,
        name="Full Compliance",
        group_type="school",
        settings={
            "age_verification_enabled": True,
            "parental_controls_enabled": True,
            "privacy": {
                "data_minimization": True,
                "data_sharing_enabled": False,
                "geolocation_enabled": False,
                "profiling_enabled": False,
                "privacy_by_default": True,
            },
            "aadc": {
                "best_interests_assessment": True,
                "child_friendly_privacy_notice": True,
                "privacy_tools_accessible": True,
                "community_standards_enforced": True,
                "reporting_tools_available": True,
                "no_nudge_techniques": True,
                "dpia_completed": True,
            },
        },
    )

    result = await run_gap_analysis(test_session, group.id)
    assert result["score"] == 100.0
    assert result["overall_status"] == "compliant"

    for standard in result["standards"]:
        assert standard["status"] == "compliant", f"{standard['id']} should be compliant"


@pytest.mark.asyncio
async def test_e2e_apply_defaults_and_retrieve(test_session):
    """Apply privacy defaults for a user, then retrieve them."""
    user_id = uuid4()

    # Apply defaults
    result = await apply_privacy_defaults(test_session, user_id, "young")
    assert result["age_tier"] == "young"
    assert result["settings"]["profile_visibility"] == "private"
    assert result["settings"]["geolocation_enabled"] is False

    # Retrieve
    stored = await get_privacy_defaults_for_user(test_session, user_id)
    assert stored is not None
    assert stored["age_tier"] == "young"
    assert stored["settings"]["profiling_enabled"] is False


@pytest.mark.asyncio
async def test_e2e_privacy_defaults_all_tiers(test_session):
    """All three age tiers should return valid privacy settings."""
    for tier in ("young", "preteen", "teen"):
        defaults = get_default_privacy_settings(tier)
        assert defaults["age_tier"] == tier
        assert isinstance(defaults["settings"], dict)
        # All tiers have geolocation off
        assert defaults["settings"]["geolocation_enabled"] is False
        # All tiers have profiling off
        assert defaults["settings"]["profiling_enabled"] is False
        # All tiers are private by default
        assert defaults["settings"]["profile_visibility"] == "private"


@pytest.mark.asyncio
async def test_e2e_multiple_assessments_history(test_session):
    """Running multiple gap analyses should create retrievable history."""
    group, owner_id = await make_test_group(test_session, name="History Test", group_type="family")

    # Run 3 assessments
    for i in range(3):
        await run_gap_analysis(test_session, group.id, assessor=f"assessor-{i}")

    history = await get_assessment_history(test_session, group.id)
    assert len(history) == 3
    # Should be newest first
    assert history[0]["assessor"] == "assessor-2"
    assert history[2]["assessor"] == "assessor-0"


@pytest.mark.asyncio
async def test_e2e_gap_analysis_nonexistent_group(test_session):
    """Gap analysis for nonexistent group should fail."""
    with pytest.raises(NotFoundError):
        await run_gap_analysis(test_session, uuid4())


@pytest.mark.asyncio
async def test_e2e_apply_defaults_invalid_tier(test_session):
    """Applying defaults with invalid tier should fail."""
    with pytest.raises(ValidationError, match="Invalid age tier"):
        await apply_privacy_defaults(test_session, uuid4(), "infant")


@pytest.mark.asyncio
async def test_e2e_young_tier_maximum_restrictions(test_session):
    """Young tier should have the strictest privacy settings."""
    user_id = uuid4()
    result = await apply_privacy_defaults(test_session, user_id, "young")
    settings = result["settings"]

    # Young tier should have everything locked down
    assert settings["profile_visibility"] == "private"
    assert settings["geolocation_enabled"] is False
    assert settings["profiling_enabled"] is False
    assert settings["data_sharing_enabled"] is False
    assert settings["search_visible"] is False
    assert settings["contact_requests_enabled"] is False
    assert settings["direct_messages_enabled"] is False
    assert settings["content_recommendations_enabled"] is False
    assert settings["analytics_tracking_enabled"] is False
    assert settings["third_party_sharing_enabled"] is False


@pytest.mark.asyncio
async def test_e2e_teen_vs_young_tier_differences(test_session):
    """Teen tier should be less restrictive than young tier for social features."""
    young = get_default_privacy_settings("young")["settings"]
    teen = get_default_privacy_settings("teen")["settings"]

    # Both have privacy core locked
    assert young["geolocation_enabled"] == teen["geolocation_enabled"] is False
    assert young["profiling_enabled"] == teen["profiling_enabled"] is False

    # Teen has more social features
    assert teen["search_visible"] is True
    assert young["search_visible"] is False
    assert teen["content_recommendations_enabled"] is True
    assert young["content_recommendations_enabled"] is False


@pytest.mark.asyncio
async def test_e2e_gap_analysis_standard_structure(test_session):
    """Each standard in the analysis should have the expected fields."""
    group, owner_id = await make_test_group(test_session, name="Structure Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    for standard in result["standards"]:
        assert "id" in standard
        assert "name" in standard
        assert "description" in standard
        assert "ico_reference" in standard
        assert "status" in standard
        assert "recommendations" in standard
        assert isinstance(standard["recommendations"], list)


@pytest.mark.asyncio
async def test_e2e_overwrite_privacy_defaults(test_session):
    """Applying new defaults should be retrievable (latest wins)."""
    user_id = uuid4()

    await apply_privacy_defaults(test_session, user_id, "young")
    await apply_privacy_defaults(test_session, user_id, "teen")

    result = await get_privacy_defaults_for_user(test_session, user_id)
    assert result is not None
    assert result["age_tier"] == "teen"
