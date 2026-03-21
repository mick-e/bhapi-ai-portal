"""End-to-end tests for EU AI Act governance module.

Full compliance workflow: assessment -> tech docs -> risk management -> bias test -> status check.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
    """Create an E2E test engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def e2e_session(e2e_engine):
    """Create an E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def e2e_data(e2e_session):
    """Create test data for E2E tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"euai-e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="EU AI Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="EU AI E2E School",
        type="school",
        owner_id=user.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    return {"user": user, "group": group}


@pytest.fixture
async def authed_e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated for E2E tests."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_data["user"].id,
            group_id=e2e_data["group"].id,
            role="admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest.fixture
async def unauthed_e2e_client(e2e_engine, e2e_session):
    """HTTP client WITHOUT auth."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Full compliance workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_compliance_workflow(authed_e2e_client, e2e_data):
    """Full workflow: assessment -> tech docs -> risk -> bias -> status."""
    group_id = str(e2e_data["group"].id)

    # 1. Create conformity assessment
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "E2E Tester"},
    )
    assert resp.status_code == 201
    assessment = resp.json()
    assert assessment["status"] == "draft"
    assert assessment["version"] == 1

    # 2. Generate tech docs
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": group_id,
            "system_name": "Safety Monitor",
            "system_description": "AI usage monitoring system",
        },
    )
    assert resp.status_code == 201
    docs = resp.json()
    assert docs["version"] == 1
    assert "general_description" in docs["sections"]

    # 3. Risk management
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/risk-management",
        json={
            "group_id": group_id,
            "risk_type": "safety",
            "description": "Child exposure to harmful content",
            "severity": "high",
            "likelihood": "medium",
            "mitigation": "Real-time content filtering and monitoring",
        },
    )
    assert resp.status_code == 201
    risk = resp.json()
    assert risk["risk_type"] == "safety"
    assert risk["residual_risk"] in ["low", "medium", "high"]

    # 4. Bias test
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": group_id,
            "model_id": "safety-classifier-v1",
            "test_data": {"samples": [{"text": "test", "expected": "safe"}]},
        },
    )
    assert resp.status_code == 201
    bias = resp.json()
    assert bias["overall_score"] >= 0
    assert "protected_characteristics" in bias["results"]

    # 5. Check compliance status
    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": group_id},
    )
    assert resp.status_code == 200
    status = resp.json()
    assert status["overall_readiness_score"] == 100
    assert status["status"] == "compliant"


# ---------------------------------------------------------------------------
# Conformity Assessment E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_assessment_endpoint(authed_e2e_client, e2e_data):
    """POST /eu-ai-act/assessment creates assessment."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={
            "group_id": str(e2e_data["group"].id),
            "assessor": "Test Assessor",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["assessor"] == "Test Assessor"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_get_assessment_endpoint(authed_e2e_client, e2e_data):
    """GET /eu-ai-act/assessment returns compliance status."""
    group_id = str(e2e_data["group"].id)

    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/assessment",
        params={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == group_id
    assert "components" in data


@pytest.mark.asyncio
async def test_assessment_versioning_endpoint(authed_e2e_client, e2e_data):
    """Multiple assessments increment version."""
    group_id = str(e2e_data["group"].id)

    r1 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "A1"},
    )
    assert r1.json()["version"] == 1

    r2 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "A2"},
    )
    assert r2.json()["version"] == 2


@pytest.mark.asyncio
async def test_assessment_articles_coverage(authed_e2e_client, e2e_data):
    """Assessment sections cover Articles 9-15."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={
            "group_id": str(e2e_data["group"].id),
            "assessor": "Coverage Tester",
        },
    )
    sections = resp.json()["sections"]
    assert "article_9_risk_management" in sections
    assert "article_10_data_governance" in sections
    assert "article_11_technical_documentation" in sections
    assert "article_12_record_keeping" in sections
    assert "article_13_transparency" in sections
    assert "article_14_human_oversight" in sections
    assert "article_15_accuracy_robustness" in sections


# ---------------------------------------------------------------------------
# Technical Documentation E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tech_docs_endpoint(authed_e2e_client, e2e_data):
    """POST /eu-ai-act/tech-docs generates documentation."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": str(e2e_data["group"].id),
            "system_name": "AI Monitor",
            "system_description": "Monitors AI usage",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_name"] == "AI Monitor"
    assert len(data["sections"]) == 8


@pytest.mark.asyncio
async def test_tech_docs_annex_iv_sections(authed_e2e_client, e2e_data):
    """Tech docs contain all Annex IV sections."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": str(e2e_data["group"].id),
            "system_name": "Annex Test",
            "system_description": "Test",
        },
    )
    sections = resp.json()["sections"]
    for key in ["general_description", "design_specifications", "development_process",
                "monitoring_functioning", "risk_management", "data_governance",
                "human_oversight", "accuracy_robustness"]:
        assert key in sections


@pytest.mark.asyncio
async def test_tech_docs_validation(authed_e2e_client, e2e_data):
    """Tech docs validation rejects empty system_name."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": str(e2e_data["group"].id),
            "system_name": "",
            "system_description": "Test",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Risk Management E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_management_endpoint(authed_e2e_client, e2e_data):
    """POST /eu-ai-act/risk-management creates record."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/risk-management",
        json={
            "group_id": str(e2e_data["group"].id),
            "risk_type": "privacy",
            "description": "PII exposure risk",
            "severity": "high",
            "likelihood": "medium",
            "mitigation": "PII detection and redaction pipeline",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_type"] == "privacy"
    assert data["severity"] == "high"
    assert "residual_risk" in data


@pytest.mark.asyncio
async def test_risk_management_invalid_severity(authed_e2e_client, e2e_data):
    """Invalid severity returns 422."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/risk-management",
        json={
            "group_id": str(e2e_data["group"].id),
            "risk_type": "safety",
            "description": "Test",
            "severity": "critical",
            "likelihood": "low",
            "mitigation": "Test",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_risk_management_invalid_risk_type(authed_e2e_client, e2e_data):
    """Invalid risk type returns 422."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/risk-management",
        json={
            "group_id": str(e2e_data["group"].id),
            "risk_type": "unknown",
            "description": "Test",
            "severity": "low",
            "likelihood": "low",
            "mitigation": "Test",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_multiple_risk_records(authed_e2e_client, e2e_data):
    """Multiple risk records can be created."""
    group_id = str(e2e_data["group"].id)

    for rt in ["safety", "privacy", "fairness"]:
        resp = await authed_e2e_client.post(
            "/api/v1/governance/eu-ai-act/risk-management",
            json={
                "group_id": group_id,
                "risk_type": rt,
                "description": f"Risk: {rt}",
                "severity": "medium",
                "likelihood": "low",
                "mitigation": "Standard mitigation",
            },
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Bias Testing E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bias_test_endpoint(authed_e2e_client, e2e_data):
    """POST /eu-ai-act/bias-test runs test."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": str(e2e_data["group"].id),
            "model_id": "safety-v1",
            "test_data": {"samples": [{"text": "hello", "expected": "safe"}]},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["model_id"] == "safety-v1"
    assert 0 <= data["overall_score"] <= 100


@pytest.mark.asyncio
async def test_bias_test_protected_chars(authed_e2e_client, e2e_data):
    """Bias test covers all protected characteristics."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": str(e2e_data["group"].id),
            "model_id": "chars-test",
            "test_data": {"samples": [{"text": "test", "expected": "safe"}]},
        },
    )
    chars = resp.json()["results"]["protected_characteristics"]
    for c in ["age", "gender", "race_ethnicity", "disability",
              "religion", "sexual_orientation", "nationality"]:
        assert c in chars


@pytest.mark.asyncio
async def test_bias_test_hash_reproducibility(authed_e2e_client, e2e_data):
    """Same test data produces same hash."""
    group_id = str(e2e_data["group"].id)
    test_data = {"samples": [{"text": "same", "expected": "safe"}]}

    r1 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={"group_id": group_id, "model_id": "m1", "test_data": test_data},
    )
    r2 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={"group_id": group_id, "model_id": "m2", "test_data": test_data},
    )
    assert r1.json()["test_data_hash"] == r2.json()["test_data_hash"]


@pytest.mark.asyncio
async def test_bias_test_validation(authed_e2e_client, e2e_data):
    """Missing model_id returns 422."""
    resp = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": str(e2e_data["group"].id),
            "model_id": "",
            "test_data": {"samples": []},
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Compliance Status E2E
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_empty_group(authed_e2e_client, e2e_data):
    """Status for empty group shows non-compliant."""
    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": str(e2e_data["group"].id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "non_compliant"
    assert data["overall_readiness_score"] == 0


@pytest.mark.asyncio
async def test_status_partial_compliance(authed_e2e_client, e2e_data):
    """Status with some components shows partial score."""
    group_id = str(e2e_data["group"].id)

    await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "Partial"},
    )

    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": group_id},
    )
    data = resp.json()
    assert data["overall_readiness_score"] == 25
    assert data["status"] == "non_compliant"


@pytest.mark.asyncio
async def test_status_includes_deadline(authed_e2e_client, e2e_data):
    """Status includes EU AI Act deadline."""
    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": str(e2e_data["group"].id)},
    )
    assert "eu_ai_act_deadline" in resp.json()


@pytest.mark.asyncio
async def test_status_components_structure(authed_e2e_client, e2e_data):
    """Status components have expected structure."""
    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": str(e2e_data["group"].id)},
    )
    components = resp.json()["components"]
    for key in ["conformity_assessment", "technical_documentation",
                "risk_management", "bias_testing"]:
        assert key in components
        assert "exists" in components[key]
        assert "status" in components[key]


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_requires_auth(unauthed_e2e_client):
    """POST /eu-ai-act/assessment without auth returns 401."""
    resp = await unauthed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": str(uuid.uuid4()), "assessor": "Test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tech_docs_requires_auth(unauthed_e2e_client):
    """POST /eu-ai-act/tech-docs without auth returns 401."""
    resp = await unauthed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": str(uuid.uuid4()),
            "system_name": "Test",
            "system_description": "Test",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_risk_requires_auth(unauthed_e2e_client):
    """POST /eu-ai-act/risk-management without auth returns 401."""
    resp = await unauthed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/risk-management",
        json={
            "group_id": str(uuid.uuid4()),
            "risk_type": "safety",
            "description": "Test",
            "severity": "low",
            "likelihood": "low",
            "mitigation": "Test",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bias_test_requires_auth(unauthed_e2e_client):
    """POST /eu-ai-act/bias-test without auth returns 401."""
    resp = await unauthed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": str(uuid.uuid4()),
            "model_id": "test",
            "test_data": {"samples": []},
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_status_requires_auth(unauthed_e2e_client):
    """GET /eu-ai-act/status without auth returns 401."""
    resp = await unauthed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_assessment_requires_auth(unauthed_e2e_client):
    """GET /eu-ai-act/assessment without auth returns 401."""
    resp = await unauthed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/assessment",
        params={"group_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Additional E2E: edge cases and workflow variations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tech_docs_versioning_endpoint(authed_e2e_client, e2e_data):
    """Multiple tech docs increment version."""
    group_id = str(e2e_data["group"].id)

    r1 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": group_id,
            "system_name": "V1",
            "system_description": "First",
        },
    )
    assert r1.json()["version"] == 1

    r2 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": group_id,
            "system_name": "V2",
            "system_description": "Second",
        },
    )
    assert r2.json()["version"] == 2


@pytest.mark.asyncio
async def test_risk_management_all_types(authed_e2e_client, e2e_data):
    """All valid risk types can be submitted."""
    group_id = str(e2e_data["group"].id)
    for rt in ["safety", "privacy", "fairness", "transparency", "accountability", "security"]:
        resp = await authed_e2e_client.post(
            "/api/v1/governance/eu-ai-act/risk-management",
            json={
                "group_id": group_id,
                "risk_type": rt,
                "description": f"Testing {rt}",
                "severity": "low",
                "likelihood": "low",
                "mitigation": "Addressed",
            },
        )
        assert resp.status_code == 201, f"Failed for risk type: {rt}"


@pytest.mark.asyncio
async def test_bias_test_different_data_different_hash(authed_e2e_client, e2e_data):
    """Different test data produces different hash."""
    group_id = str(e2e_data["group"].id)

    r1 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": group_id,
            "model_id": "m1",
            "test_data": {"samples": [{"text": "data1", "expected": "safe"}]},
        },
    )
    r2 = await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": group_id,
            "model_id": "m1",
            "test_data": {"samples": [{"text": "data2", "expected": "unsafe"}]},
        },
    )
    assert r1.json()["test_data_hash"] != r2.json()["test_data_hash"]


@pytest.mark.asyncio
async def test_status_half_compliance(authed_e2e_client, e2e_data):
    """Status with 2 components shows 50% score."""
    group_id = str(e2e_data["group"].id)

    await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "Half"},
    )
    await authed_e2e_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": group_id,
            "system_name": "Half System",
            "system_description": "Half compliance",
        },
    )

    resp = await authed_e2e_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": group_id},
    )
    data = resp.json()
    assert data["overall_readiness_score"] == 50
    assert data["status"] == "non_compliant"
