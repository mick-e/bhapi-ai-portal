"""Security tests for EU AI Act governance module.

Tests admin-only access, multi-tenant isolation, and assessment versioning integrity.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.governance.eu_ai_act import (
    ConformityAssessment,
    create_conformity_assessment,
    generate_tech_documentation,
    get_compliance_status,
    run_bias_test,
    run_risk_management_assessment,
)
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sec_engine():
    """Create a security test engine."""
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
async def sec_session(sec_engine):
    """Create a security test session."""
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def sec_data(sec_session):
    """Create test data for security tests — two separate groups."""
    # User 1 (owner of group 1)
    user1 = User(
        id=uuid.uuid4(),
        email=f"sec1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security User 1",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    # User 2 (owner of group 2)
    user2 = User(
        id=uuid.uuid4(),
        email=f"sec2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security User 2",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()

    group1 = Group(id=uuid.uuid4(), name="School 1", type="school", owner_id=user1.id)
    group2 = Group(id=uuid.uuid4(), name="School 2", type="school", owner_id=user2.id)
    sec_session.add_all([group1, group2])
    await sec_session.flush()

    return {
        "user1": user1,
        "user2": user2,
        "group1": group1,
        "group2": group2,
    }


@pytest.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def authed_client_user1(sec_engine, sec_session, sec_data):
    """HTTP client authenticated as user1."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_data["user1"].id,
            group_id=sec_data["group1"].id,
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
async def authed_client_user2(sec_engine, sec_session, sec_data):
    """HTTP client authenticated as user2."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_data["user2"].id,
            group_id=sec_data["group2"].id,
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


# ---------------------------------------------------------------------------
# Auth enforcement tests (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_create_requires_auth(unauthed_client):
    """POST /eu-ai-act/assessment without auth returns 401."""
    resp = await unauthed_client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": str(uuid.uuid4()), "assessor": "Test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_assessment_get_requires_auth(unauthed_client):
    """GET /eu-ai-act/assessment without auth returns 401."""
    resp = await unauthed_client.get(
        "/api/v1/governance/eu-ai-act/assessment",
        params={"group_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tech_docs_requires_auth(unauthed_client):
    """POST /eu-ai-act/tech-docs without auth returns 401."""
    resp = await unauthed_client.post(
        "/api/v1/governance/eu-ai-act/tech-docs",
        json={
            "group_id": str(uuid.uuid4()),
            "system_name": "Test",
            "system_description": "Test",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_risk_management_requires_auth(unauthed_client):
    """POST /eu-ai-act/risk-management without auth returns 401."""
    resp = await unauthed_client.post(
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
async def test_bias_test_requires_auth(unauthed_client):
    """POST /eu-ai-act/bias-test without auth returns 401."""
    resp = await unauthed_client.post(
        "/api/v1/governance/eu-ai-act/bias-test",
        json={
            "group_id": str(uuid.uuid4()),
            "model_id": "test",
            "test_data": {"samples": []},
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_status_requires_auth(unauthed_client):
    """GET /eu-ai-act/status without auth returns 401."""
    resp = await unauthed_client.get(
        "/api/v1/governance/eu-ai-act/status",
        params={"group_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Multi-tenant isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_tenant_isolation(sec_session, sec_data):
    """Assessment for group1 not visible to group2 status."""
    # Create assessment for group1
    await create_conformity_assessment(
        sec_session,
        group_id=sec_data["group1"].id,
        assessor="Group1 Assessor",
    )

    # Group2 status should show no assessment
    status = await get_compliance_status(sec_session, sec_data["group2"].id)
    assert status["components"]["conformity_assessment"]["exists"] is False


@pytest.mark.asyncio
async def test_tech_docs_tenant_isolation(sec_session, sec_data):
    """Tech docs for group1 not visible to group2."""
    await generate_tech_documentation(
        sec_session,
        group_id=sec_data["group1"].id,
        system_name="Group1 System",
        system_description="Isolated system",
    )

    status = await get_compliance_status(sec_session, sec_data["group2"].id)
    assert status["components"]["technical_documentation"]["exists"] is False


@pytest.mark.asyncio
async def test_risk_records_tenant_isolation(sec_session, sec_data):
    """Risk records for group1 not visible to group2."""
    await run_risk_management_assessment(
        sec_session,
        group_id=sec_data["group1"].id,
        risk_type="safety",
        description="Group1 risk",
        severity="high",
        likelihood="low",
        mitigation="Mitigation",
    )

    status = await get_compliance_status(sec_session, sec_data["group2"].id)
    assert status["components"]["risk_management"]["exists"] is False


@pytest.mark.asyncio
async def test_bias_test_tenant_isolation(sec_session, sec_data):
    """Bias test for group1 not visible to group2."""
    await run_bias_test(
        sec_session,
        group_id=sec_data["group1"].id,
        model_id="isolated-model",
        test_data={"samples": [{"text": "test", "expected": "safe"}]},
    )

    status = await get_compliance_status(sec_session, sec_data["group2"].id)
    assert status["components"]["bias_testing"]["exists"] is False


@pytest.mark.asyncio
async def test_full_isolation_both_groups(sec_session, sec_data):
    """Both groups can have independent compliance data."""
    # Group 1 gets everything
    await create_conformity_assessment(sec_session, sec_data["group1"].id, "A1")
    await generate_tech_documentation(sec_session, sec_data["group1"].id, "S1", "D1")
    await run_risk_management_assessment(
        sec_session, sec_data["group1"].id, "safety", "R1", "low", "low", "M1")
    await run_bias_test(
        sec_session, sec_data["group1"].id, "m1", {"samples": [{"text": "t", "expected": "s"}]})

    # Group 2 gets only assessment
    await create_conformity_assessment(sec_session, sec_data["group2"].id, "A2")

    s1 = await get_compliance_status(sec_session, sec_data["group1"].id)
    s2 = await get_compliance_status(sec_session, sec_data["group2"].id)

    assert s1["overall_readiness_score"] == 100
    assert s2["overall_readiness_score"] == 25


# ---------------------------------------------------------------------------
# Assessment versioning integrity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assessment_version_monotonic(sec_session, sec_data):
    """Assessment versions always increase."""
    results = []
    for i in range(5):
        r = await create_conformity_assessment(
            sec_session,
            group_id=sec_data["group1"].id,
            assessor=f"Assessor {i}",
        )
        results.append(r["version"])

    assert results == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_assessment_version_independent_per_group(sec_session, sec_data):
    """Each group has independent version numbering."""
    r1 = await create_conformity_assessment(
        sec_session, sec_data["group1"].id, "A1")
    r2 = await create_conformity_assessment(
        sec_session, sec_data["group2"].id, "A2")

    assert r1["version"] == 1
    assert r2["version"] == 1


@pytest.mark.asyncio
async def test_assessment_sections_immutable_after_approval(sec_session, sec_data):
    """Approved assessment cannot be changed back to draft."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import update_assessment_status

    r = await create_conformity_assessment(
        sec_session, sec_data["group1"].id, "Approver")
    assessment_id = uuid.UUID(r["assessment_id"])

    await update_assessment_status(sec_session, assessment_id, "submitted")
    await update_assessment_status(sec_session, assessment_id, "approved")

    with pytest.raises(ValidationError):
        await update_assessment_status(sec_session, assessment_id, "draft")


@pytest.mark.asyncio
async def test_assessment_status_cannot_skip_to_approved(sec_session, sec_data):
    """Assessment cannot go directly from draft to approved."""
    from src.exceptions import ValidationError
    from src.governance.eu_ai_act import update_assessment_status

    r = await create_conformity_assessment(
        sec_session, sec_data["group1"].id, "Skipper")
    assessment_id = uuid.UUID(r["assessment_id"])

    with pytest.raises(ValidationError):
        await update_assessment_status(sec_session, assessment_id, "approved")
