"""Unit tests for UK AADC compliance — gap analysis and privacy-by-default.

Tests cover:
- Gap analysis returning 15 AADC standards with compliance status
- Privacy-by-default enforcement per age tier (young, preteen, teen)
- Assessment persistence and history retrieval
- Validation of invalid inputs
"""

from uuid import uuid4

import pytest

from src.compliance.uk_aadc import (
    AADC_STANDARD_IDS,
    AADC_STANDARDS,
    apply_privacy_defaults,
    get_assessment_history,
    get_default_privacy_settings,
    get_latest_assessment,
    get_privacy_defaults_for_user,
    run_gap_analysis,
)
from src.exceptions import NotFoundError, ValidationError
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Gap analysis tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aadc_gap_analysis_returns_15_standards(test_session):
    """Gap analysis must return exactly 15 AADC standards."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    assert len(result["standards"]) == 15
    returned_ids = [s["id"] for s in result["standards"]]
    for std_id in AADC_STANDARD_IDS:
        assert std_id in returned_ids


@pytest.mark.asyncio
async def test_aadc_gap_analysis_standard_statuses(test_session):
    """Each standard must have a valid status: compliant, partial, or non_compliant."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    valid_statuses = {"compliant", "partial", "non_compliant"}
    for standard in result["standards"]:
        assert standard["status"] in valid_statuses, f"{standard['id']} has invalid status: {standard['status']}"


@pytest.mark.asyncio
async def test_aadc_gap_analysis_identifies_non_compliant(test_session):
    """Default group settings should produce some non-compliant standards."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    non_compliant = [s for s in result["standards"] if s["status"] == "non_compliant"]
    assert len(non_compliant) > 0, "A default group should have non-compliant standards"


@pytest.mark.asyncio
async def test_aadc_gap_analysis_with_compliant_settings(test_session):
    """Group with full AADC settings should have higher compliance score."""
    group, owner_id = await make_test_group(
        test_session,
        name="Compliant Group",
        group_type="family",
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
    compliant = [s for s in result["standards"] if s["status"] == "compliant"]
    assert len(compliant) == 15


@pytest.mark.asyncio
async def test_aadc_gap_analysis_score_calculation(test_session):
    """Score should be between 0 and 100."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    assert 0 <= result["score"] <= 100
    assert result["overall_status"] in {"compliant", "partial", "non_compliant"}


@pytest.mark.asyncio
async def test_aadc_gap_analysis_persists_assessment(test_session):
    """Gap analysis should persist the assessment to the database."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    assert "id" in result
    assert result["group_id"] == str(group.id)
    assert result["assessed_at"] is not None


@pytest.mark.asyncio
async def test_aadc_gap_analysis_nonexistent_group(test_session):
    """Gap analysis for nonexistent group should raise NotFoundError."""
    fake_id = uuid4()
    with pytest.raises(NotFoundError):
        await run_gap_analysis(test_session, fake_id)


@pytest.mark.asyncio
async def test_aadc_gap_analysis_recommendations(test_session):
    """Non-compliant standards should include recommendations."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    result = await run_gap_analysis(test_session, group.id)

    for standard in result["standards"]:
        if standard["status"] != "compliant":
            assert len(standard["recommendations"]) > 0, (
                f"{standard['id']} is {standard['status']} but has no recommendations"
            )
        else:
            assert standard["recommendations"] == []


# ---------------------------------------------------------------------------
# Privacy-by-default tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_privacy_by_default_young_tier(test_session):
    """Young tier (5-9) must have maximum privacy: all sharing disabled."""
    defaults = get_default_privacy_settings("young")

    assert defaults["age_tier"] == "young"
    settings = defaults["settings"]
    assert settings["profile_visibility"] == "private"
    assert settings["geolocation_enabled"] is False
    assert settings["profiling_enabled"] is False
    assert settings["data_sharing_enabled"] is False
    assert settings["search_visible"] is False
    assert settings["contact_requests_enabled"] is False
    assert settings["direct_messages_enabled"] is False


@pytest.mark.asyncio
async def test_privacy_by_default_preteen_tier(test_session):
    """Preteen tier (10-12) has maximum privacy with limited social features."""
    defaults = get_default_privacy_settings("preteen")

    settings = defaults["settings"]
    assert settings["profile_visibility"] == "private"
    assert settings["geolocation_enabled"] is False
    assert settings["profiling_enabled"] is False
    assert settings["data_sharing_enabled"] is False
    assert settings["contact_requests_enabled"] is True
    assert settings["direct_messages_enabled"] is True


@pytest.mark.asyncio
async def test_privacy_by_default_teen_tier(test_session):
    """Teen tier (13-15) has maximum privacy with more social features enabled."""
    defaults = get_default_privacy_settings("teen")

    settings = defaults["settings"]
    assert settings["profile_visibility"] == "private"
    assert settings["geolocation_enabled"] is False
    assert settings["profiling_enabled"] is False
    assert settings["data_sharing_enabled"] is False
    assert settings["search_visible"] is True
    assert settings["content_recommendations_enabled"] is True


@pytest.mark.asyncio
async def test_privacy_by_default_invalid_tier(test_session):
    """Invalid age tier should raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid age tier"):
        get_default_privacy_settings("adult")


@pytest.mark.asyncio
async def test_apply_privacy_defaults(test_session):
    """Applying privacy defaults should persist settings for the user."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    user_id = uuid4()

    # Create a user first for FK safety (though model doesn't have FK)
    result = await apply_privacy_defaults(test_session, user_id, "young")

    assert result["user_id"] == str(user_id)
    assert result["age_tier"] == "young"
    assert result["settings"]["profile_visibility"] == "private"
    assert result["settings"]["geolocation_enabled"] is False


@pytest.mark.asyncio
async def test_apply_privacy_defaults_invalid_tier(test_session):
    """Applying defaults with invalid tier should raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid age tier"):
        await apply_privacy_defaults(test_session, uuid4(), "toddler")


@pytest.mark.asyncio
async def test_get_privacy_defaults_for_user(test_session):
    """Should retrieve the most recent privacy defaults for a user."""
    user_id = uuid4()
    await apply_privacy_defaults(test_session, user_id, "young")

    result = await get_privacy_defaults_for_user(test_session, user_id)
    assert result is not None
    assert result["age_tier"] == "young"
    assert result["settings"]["geolocation_enabled"] is False


@pytest.mark.asyncio
async def test_get_privacy_defaults_nonexistent_user(test_session):
    """Should return None for a user with no privacy defaults."""
    result = await get_privacy_defaults_for_user(test_session, uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Assessment history tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_history(test_session):
    """Multiple assessments should be returned in reverse chronological order."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")

    await run_gap_analysis(test_session, group.id, assessor="first")
    await run_gap_analysis(test_session, group.id, assessor="second")

    history = await get_assessment_history(test_session, group.id)
    assert len(history) == 2
    assert history[0]["assessor"] == "second"
    assert history[1]["assessor"] == "first"


@pytest.mark.asyncio
async def test_latest_assessment(test_session):
    """Latest assessment should return the most recent one."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")

    await run_gap_analysis(test_session, group.id, assessor="first")
    await run_gap_analysis(test_session, group.id, assessor="latest")

    latest = await get_latest_assessment(test_session, group.id)
    assert latest is not None
    assert latest["assessor"] == "latest"


@pytest.mark.asyncio
async def test_latest_assessment_no_history(test_session):
    """Latest assessment should return None if no assessments exist."""
    group, owner_id = await make_test_group(test_session, name="AADC Test", group_type="family")
    latest = await get_latest_assessment(test_session, group.id)
    assert latest is None


# ---------------------------------------------------------------------------
# Standards definition tests
# ---------------------------------------------------------------------------


def test_aadc_standards_count():
    """There must be exactly 15 AADC standards defined."""
    assert len(AADC_STANDARDS) == 15
    assert len(AADC_STANDARD_IDS) == 15


def test_aadc_standards_have_required_fields():
    """Each AADC standard must have id, name, description, ico_reference."""
    for std in AADC_STANDARDS:
        assert "id" in std
        assert "name" in std
        assert "description" in std
        assert "ico_reference" in std


def test_aadc_standard_ids_unique():
    """All AADC standard IDs must be unique."""
    assert len(set(AADC_STANDARD_IDS)) == len(AADC_STANDARD_IDS)
