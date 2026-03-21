"""Unit tests for EU AI Act governance module.

Tests conformity assessment, technical documentation, risk management,
and bias testing per EU AI Act requirements.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.groups.models import Group


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def school_group(test_session: AsyncSession):
    """Create a school group with owner for EU AI Act tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"euai-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="EU AI Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="EU AI Test School",
        type="school",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    return {"group": group, "owner": user}


# ---------------------------------------------------------------------------
# Conformity Assessment Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conformity_assessment_structure(test_session, school_group):
    """Conformity assessment covers all required EU AI Act articles (Article 9-15)."""
    from src.governance.eu_ai_act import create_conformity_assessment

    result = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Test Assessor",
    )

    assert result["status"] == "draft"
    assert result["assessor"] == "Test Assessor"
    assert result["version"] == 1

    sections = result["sections"]
    required_articles = [
        "article_9_risk_management",
        "article_10_data_governance",
        "article_11_technical_documentation",
        "article_12_record_keeping",
        "article_13_transparency",
        "article_14_human_oversight",
        "article_15_accuracy_robustness",
    ]
    for article in required_articles:
        assert article in sections, f"Missing required article: {article}"
        assert "status" in sections[article]
        assert "findings" in sections[article]
        assert "recommendations" in sections[article]


@pytest.mark.asyncio
async def test_conformity_assessment_creates_db_record(test_session, school_group):
    """Conformity assessment persists to database."""
    from src.governance.eu_ai_act import (
        ConformityAssessment,
        create_conformity_assessment,
    )
    from sqlalchemy import select

    result = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="DB Tester",
    )

    record = await test_session.execute(
        select(ConformityAssessment).where(
            ConformityAssessment.group_id == school_group["group"].id,
        )
    )
    assessment = record.scalars().first()
    assert assessment is not None
    assert assessment.assessor == "DB Tester"
    assert assessment.status == "draft"


@pytest.mark.asyncio
async def test_conformity_assessment_versioning(test_session, school_group):
    """Creating multiple assessments increments version."""
    from src.governance.eu_ai_act import create_conformity_assessment

    r1 = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Assessor 1",
    )
    assert r1["version"] == 1

    r2 = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Assessor 2",
    )
    assert r2["version"] == 2


@pytest.mark.asyncio
async def test_conformity_assessment_status_transitions(test_session, school_group):
    """Assessment status can transition: draft -> submitted -> approved."""
    from src.governance.eu_ai_act import (
        create_conformity_assessment,
        update_assessment_status,
    )

    result = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Status Tester",
    )
    assessment_id = uuid.UUID(result["assessment_id"])

    # draft -> submitted
    updated = await update_assessment_status(test_session, assessment_id, "submitted")
    assert updated["status"] == "submitted"

    # submitted -> approved
    updated = await update_assessment_status(test_session, assessment_id, "approved")
    assert updated["status"] == "approved"


@pytest.mark.asyncio
async def test_conformity_assessment_invalid_status(test_session, school_group):
    """Invalid status transition raises ValidationError."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import (
        create_conformity_assessment,
        update_assessment_status,
    )

    result = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Invalid Tester",
    )
    assessment_id = uuid.UUID(result["assessment_id"])

    with pytest.raises(ValidationError):
        await update_assessment_status(test_session, assessment_id, "invalid_status")


# ---------------------------------------------------------------------------
# Technical Documentation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_technical_documentation_generation(test_session, school_group):
    """Tech docs include all Annex IV required elements."""
    from src.governance.eu_ai_act import generate_tech_documentation

    result = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="AI Safety Monitor",
        system_description="Monitors child AI usage for safety risks",
    )

    assert result["system_name"] == "AI Safety Monitor"
    sections = result["sections"]
    required_sections = [
        "general_description",
        "design_specifications",
        "development_process",
        "monitoring_functioning",
        "risk_management",
        "data_governance",
        "human_oversight",
        "accuracy_robustness",
    ]
    for section in required_sections:
        assert section in sections, f"Missing required Annex IV section: {section}"
        assert "content" in sections[section]
        assert "status" in sections[section]


@pytest.mark.asyncio
async def test_tech_docs_creates_db_record(test_session, school_group):
    """Technical documentation persists to database."""
    from src.governance.eu_ai_act import TechnicalDocumentation, generate_tech_documentation
    from sqlalchemy import select

    await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="Test System",
        system_description="Test description",
    )

    record = await test_session.execute(
        select(TechnicalDocumentation).where(
            TechnicalDocumentation.group_id == school_group["group"].id,
        )
    )
    doc = record.scalars().first()
    assert doc is not None
    assert doc.version == 1


@pytest.mark.asyncio
async def test_tech_docs_versioning(test_session, school_group):
    """Generating docs again increments version."""
    from src.governance.eu_ai_act import generate_tech_documentation

    r1 = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="System v1",
        system_description="First version",
    )
    assert r1["version"] == 1

    r2 = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="System v2",
        system_description="Second version",
    )
    assert r2["version"] == 2


@pytest.mark.asyncio
async def test_tech_docs_general_description_content(test_session, school_group):
    """General description section contains system name and description."""
    from src.governance.eu_ai_act import generate_tech_documentation

    result = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="Child Safety AI",
        system_description="Monitors and protects children online",
    )
    general = result["sections"]["general_description"]
    assert "Child Safety AI" in general["content"]
    assert "Monitors and protects children online" in general["content"]


@pytest.mark.asyncio
async def test_tech_docs_requires_system_name(test_session, school_group):
    """Tech docs require a system name."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import generate_tech_documentation

    with pytest.raises(ValidationError):
        await generate_tech_documentation(
            db=test_session,
            group_id=school_group["group"].id,
            system_name="",
            system_description="Test",
        )


# ---------------------------------------------------------------------------
# Risk Management Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_management_assessment(test_session, school_group):
    """Risk management assessment creates records per Article 9."""
    from src.governance.eu_ai_act import run_risk_management_assessment

    result = await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="Child exposure to harmful content",
        severity="high",
        likelihood="medium",
        mitigation="Content filtering and real-time monitoring",
    )

    assert result["risk_type"] == "safety"
    assert result["severity"] == "high"
    assert result["likelihood"] == "medium"
    assert result["mitigation"] == "Content filtering and real-time monitoring"
    assert "residual_risk" in result
    assert "record_id" in result


@pytest.mark.asyncio
async def test_risk_management_creates_db_record(test_session, school_group):
    """Risk management record persists to database."""
    from src.governance.eu_ai_act import RiskManagementRecord, run_risk_management_assessment
    from sqlalchemy import select

    await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="privacy",
        description="PII exposure in AI prompts",
        severity="high",
        likelihood="high",
        mitigation="PII detection and redaction",
    )

    record = await test_session.execute(
        select(RiskManagementRecord).where(
            RiskManagementRecord.group_id == school_group["group"].id,
        )
    )
    risk = record.scalars().first()
    assert risk is not None
    assert risk.risk_type == "privacy"
    assert risk.severity == "high"


@pytest.mark.asyncio
async def test_risk_management_severity_validation(test_session, school_group):
    """Invalid severity raises ValidationError."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_risk_management_assessment

    with pytest.raises(ValidationError):
        await run_risk_management_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            risk_type="safety",
            description="Test",
            severity="extreme",  # invalid
            likelihood="low",
            mitigation="None",
        )


@pytest.mark.asyncio
async def test_risk_management_likelihood_validation(test_session, school_group):
    """Invalid likelihood raises ValidationError."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_risk_management_assessment

    with pytest.raises(ValidationError):
        await run_risk_management_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            risk_type="safety",
            description="Test",
            severity="low",
            likelihood="impossible",  # invalid
            mitigation="None",
        )


@pytest.mark.asyncio
async def test_risk_management_residual_risk_calculation(test_session, school_group):
    """Residual risk is calculated based on severity and mitigation."""
    from src.governance.eu_ai_act import run_risk_management_assessment

    result = await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="High risk with mitigation",
        severity="high",
        likelihood="high",
        mitigation="Comprehensive monitoring and content filtering with real-time alerts",
    )
    assert result["residual_risk"] in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_risk_management_multiple_records(test_session, school_group):
    """Multiple risk records can be created for same group."""
    from src.governance.eu_ai_act import RiskManagementRecord, run_risk_management_assessment
    from sqlalchemy import select, func

    await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="Risk 1",
        severity="high",
        likelihood="low",
        mitigation="Mitigation 1",
    )
    await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="privacy",
        description="Risk 2",
        severity="medium",
        likelihood="medium",
        mitigation="Mitigation 2",
    )

    count = await test_session.execute(
        select(func.count()).select_from(
            select(RiskManagementRecord).where(
                RiskManagementRecord.group_id == school_group["group"].id,
            ).subquery()
        )
    )
    assert count.scalar() == 2


# ---------------------------------------------------------------------------
# Bias Testing Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bias_testing_framework(test_session, school_group):
    """Bias testing covers protected characteristics per EU AI Act."""
    from src.governance.eu_ai_act import run_bias_test

    result = await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="safety-classifier-v1",
        test_data={"samples": [
            {"text": "Hello world", "expected": "safe"},
            {"text": "Bad content", "expected": "unsafe"},
        ]},
    )

    assert result["model_id"] == "safety-classifier-v1"
    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 100
    assert "results" in result

    # Must cover EU AI Act protected characteristics
    protected_chars = result["results"]["protected_characteristics"]
    required_characteristics = [
        "age",
        "gender",
        "race_ethnicity",
        "disability",
        "religion",
        "sexual_orientation",
        "nationality",
    ]
    for char in required_characteristics:
        assert char in protected_chars, f"Missing protected characteristic: {char}"
        assert "score" in protected_chars[char]
        assert "status" in protected_chars[char]


@pytest.mark.asyncio
async def test_bias_test_creates_db_record(test_session, school_group):
    """Bias test result persists to database."""
    from src.governance.eu_ai_act import BiasTestResult, run_bias_test
    from sqlalchemy import select

    await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="test-model",
        test_data={"samples": [{"text": "test", "expected": "safe"}]},
    )

    record = await test_session.execute(
        select(BiasTestResult).where(
            BiasTestResult.group_id == school_group["group"].id,
        )
    )
    bias = record.scalars().first()
    assert bias is not None
    assert bias.model_id == "test-model"
    assert bias.overall_score >= 0


@pytest.mark.asyncio
async def test_bias_test_data_hash(test_session, school_group):
    """Bias test stores a hash of test data for reproducibility."""
    from src.governance.eu_ai_act import run_bias_test

    result = await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="hash-model",
        test_data={"samples": [{"text": "test", "expected": "safe"}]},
    )
    assert "test_data_hash" in result
    assert len(result["test_data_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_bias_test_requires_model_id(test_session, school_group):
    """Bias test requires a model ID."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_bias_test

    with pytest.raises(ValidationError):
        await run_bias_test(
            db=test_session,
            group_id=school_group["group"].id,
            model_id="",
            test_data={"samples": []},
        )


@pytest.mark.asyncio
async def test_bias_test_requires_test_data(test_session, school_group):
    """Bias test requires test data with samples."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_bias_test

    with pytest.raises(ValidationError):
        await run_bias_test(
            db=test_session,
            group_id=school_group["group"].id,
            model_id="test-model",
            test_data={},
        )


@pytest.mark.asyncio
async def test_bias_test_score_range(test_session, school_group):
    """Bias test overall score is between 0 and 100."""
    from src.governance.eu_ai_act import run_bias_test

    result = await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="score-model",
        test_data={"samples": [
            {"text": "test1", "expected": "safe"},
            {"text": "test2", "expected": "unsafe"},
        ]},
    )
    assert 0 <= result["overall_score"] <= 100


# ---------------------------------------------------------------------------
# Compliance Status Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_status_empty(test_session, school_group):
    """Compliance status for group with no assessments."""
    from src.governance.eu_ai_act import get_compliance_status

    result = await get_compliance_status(
        db=test_session,
        group_id=school_group["group"].id,
    )

    assert result["group_id"] == str(school_group["group"].id)
    assert result["overall_readiness_score"] == 0
    assert result["status"] == "non_compliant"
    assert "conformity_assessment" in result["components"]
    assert "technical_documentation" in result["components"]
    assert "risk_management" in result["components"]
    assert "bias_testing" in result["components"]


@pytest.mark.asyncio
async def test_compliance_status_with_assessment(test_session, school_group):
    """Compliance status improves with conformity assessment."""
    from src.governance.eu_ai_act import create_conformity_assessment, get_compliance_status

    await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Test",
    )

    result = await get_compliance_status(
        db=test_session,
        group_id=school_group["group"].id,
    )
    assert result["overall_readiness_score"] > 0
    assert result["components"]["conformity_assessment"]["exists"] is True


@pytest.mark.asyncio
async def test_compliance_status_full(test_session, school_group):
    """Full compliance when all components exist."""
    from src.governance.eu_ai_act import (
        create_conformity_assessment,
        generate_tech_documentation,
        get_compliance_status,
        run_bias_test,
        run_risk_management_assessment,
    )

    await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Full Tester",
    )
    await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="Test System",
        system_description="Test",
    )
    await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="Test",
        severity="low",
        likelihood="low",
        mitigation="Tested",
    )
    await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="test",
        test_data={"samples": [{"text": "test", "expected": "safe"}]},
    )

    result = await get_compliance_status(
        db=test_session,
        group_id=school_group["group"].id,
    )
    assert result["overall_readiness_score"] == 100
    assert result["status"] == "compliant"
    for comp in result["components"].values():
        assert comp["exists"] is True


@pytest.mark.asyncio
async def test_compliance_status_approved_assessment_bonus(test_session, school_group):
    """Approved assessment shows as approved in status."""
    from src.governance.eu_ai_act import (
        create_conformity_assessment,
        get_compliance_status,
        update_assessment_status,
    )

    r = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Approver",
    )
    assessment_id = uuid.UUID(r["assessment_id"])
    await update_assessment_status(test_session, assessment_id, "submitted")
    await update_assessment_status(test_session, assessment_id, "approved")

    result = await get_compliance_status(
        db=test_session,
        group_id=school_group["group"].id,
    )
    assert result["components"]["conformity_assessment"]["status"] == "approved"


# ---------------------------------------------------------------------------
# Edge Cases and Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conformity_assessment_requires_assessor(test_session, school_group):
    """Assessment requires assessor name."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import create_conformity_assessment

    with pytest.raises(ValidationError):
        await create_conformity_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            assessor="",
        )


@pytest.mark.asyncio
async def test_risk_management_description_required(test_session, school_group):
    """Risk management requires description."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_risk_management_assessment

    with pytest.raises(ValidationError):
        await run_risk_management_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            risk_type="safety",
            description="",
            severity="low",
            likelihood="low",
            mitigation="Test",
        )


@pytest.mark.asyncio
async def test_assessment_not_found(test_session):
    """Updating non-existent assessment raises NotFoundError."""
    from src.exceptions import NotFoundError
    from src.governance.eu_ai_act import update_assessment_status

    with pytest.raises(NotFoundError):
        await update_assessment_status(test_session, uuid.uuid4(), "submitted")


@pytest.mark.asyncio
async def test_risk_type_validation(test_session, school_group):
    """Invalid risk type raises ValidationError."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import run_risk_management_assessment

    with pytest.raises(ValidationError):
        await run_risk_management_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            risk_type="invalid_type",
            description="Test",
            severity="low",
            likelihood="low",
            mitigation="Test",
        )


@pytest.mark.asyncio
async def test_multiple_bias_tests_same_model(test_session, school_group):
    """Multiple bias tests can exist for the same model."""
    from src.governance.eu_ai_act import BiasTestResult, run_bias_test
    from sqlalchemy import select, func

    for _ in range(3):
        await run_bias_test(
            db=test_session,
            group_id=school_group["group"].id,
            model_id="repeated-model",
            test_data={"samples": [{"text": "test", "expected": "safe"}]},
        )

    count = await test_session.execute(
        select(func.count()).select_from(
            select(BiasTestResult).where(
                BiasTestResult.group_id == school_group["group"].id,
                BiasTestResult.model_id == "repeated-model",
            ).subquery()
        )
    )
    assert count.scalar() == 3


@pytest.mark.asyncio
async def test_tech_docs_data_governance_section(test_session, school_group):
    """Data governance section references GDPR/COPPA compliance."""
    from src.governance.eu_ai_act import generate_tech_documentation

    result = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="Data Gov Test",
        system_description="Test system",
    )
    data_gov = result["sections"]["data_governance"]
    assert data_gov["status"] in ["draft", "complete", "needs_review"]


@pytest.mark.asyncio
async def test_tech_docs_human_oversight_section(test_session, school_group):
    """Human oversight section covers Article 14 requirements."""
    from src.governance.eu_ai_act import generate_tech_documentation

    result = await generate_tech_documentation(
        db=test_session,
        group_id=school_group["group"].id,
        system_name="Oversight Test",
        system_description="Test system",
    )
    oversight = result["sections"]["human_oversight"]
    assert "content" in oversight
    assert oversight["status"] in ["draft", "complete", "needs_review"]


# ---------------------------------------------------------------------------
# Additional unit tests for coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_residual_risk_low_input(test_session, school_group):
    """Low severity + low likelihood -> low residual risk."""
    from src.governance.eu_ai_act import run_risk_management_assessment

    result = await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="Minor risk",
        severity="low",
        likelihood="low",
        mitigation="Basic mitigation applied here",
    )
    assert result["residual_risk"] == "low"


@pytest.mark.asyncio
async def test_residual_risk_high_input_short_mitigation(test_session, school_group):
    """High severity + high likelihood with short mitigation -> high residual risk."""
    from src.governance.eu_ai_act import run_risk_management_assessment

    result = await run_risk_management_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        risk_type="safety",
        description="Major risk",
        severity="high",
        likelihood="high",
        mitigation="Brief",
    )
    assert result["residual_risk"] == "high"


@pytest.mark.asyncio
async def test_conformity_assessment_sections_have_evidence(test_session, school_group):
    """Each assessment section has an evidence list."""
    from src.governance.eu_ai_act import create_conformity_assessment

    result = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Evidence Tester",
    )
    for article, section in result["sections"].items():
        assert "evidence" in section, f"Missing evidence in {article}"


@pytest.mark.asyncio
async def test_compliance_status_deadline(test_session, school_group):
    """Compliance status includes the EU AI Act deadline."""
    from src.governance.eu_ai_act import get_compliance_status

    result = await get_compliance_status(
        db=test_session,
        group_id=school_group["group"].id,
    )
    assert result["eu_ai_act_deadline"] == "2026-08-02"


@pytest.mark.asyncio
async def test_bias_test_methodology_included(test_session, school_group):
    """Bias test results include methodology information."""
    from src.governance.eu_ai_act import run_bias_test

    result = await run_bias_test(
        db=test_session,
        group_id=school_group["group"].id,
        model_id="method-model",
        test_data={"samples": [{"text": "test", "expected": "safe"}]},
    )
    assert "methodology" in result["results"]
    assert result["results"]["methodology"] == "statistical_parity_and_equalized_odds"


@pytest.mark.asyncio
async def test_risk_management_all_valid_types(test_session, school_group):
    """All valid risk types are accepted."""
    from src.governance.eu_ai_act import run_risk_management_assessment

    for rt in ["safety", "privacy", "fairness", "transparency", "accountability", "security"]:
        result = await run_risk_management_assessment(
            db=test_session,
            group_id=school_group["group"].id,
            risk_type=rt,
            description=f"Test {rt}",
            severity="low",
            likelihood="low",
            mitigation="Standard",
        )
        assert result["risk_type"] == rt


@pytest.mark.asyncio
async def test_assessment_status_submitted_can_revert_to_draft(test_session, school_group):
    """Submitted assessment can go back to draft."""
    from src.governance.eu_ai_act import create_conformity_assessment, update_assessment_status

    r = await create_conformity_assessment(
        db=test_session,
        group_id=school_group["group"].id,
        assessor="Reverter",
    )
    assessment_id = uuid.UUID(r["assessment_id"])

    await update_assessment_status(test_session, assessment_id, "submitted")
    result = await update_assessment_status(test_session, assessment_id, "draft")
    assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_string_group_id_accepted(test_session, school_group):
    """String group_id is accepted and converted."""
    from src.governance.eu_ai_act import create_conformity_assessment

    result = await create_conformity_assessment(
        db=test_session,
        group_id=str(school_group["group"].id),
        assessor="String ID Tester",
    )
    assert result["group_id"] == str(school_group["group"].id)
