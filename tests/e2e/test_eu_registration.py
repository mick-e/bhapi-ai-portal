"""End-to-end tests for EU AI Act database registration submission.

Tests the registration workflow: generate payload -> validate -> submit -> track status.
Requires an approved conformity assessment before registration can proceed.
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
    REGISTRATION_REQUIRED_FIELDS,
    RegistrationSubmission,
    create_conformity_assessment,
    generate_tech_documentation,
    update_assessment_status,
)
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def reg_engine():
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
async def reg_session(reg_engine):
    """Create an E2E test session."""
    session = AsyncSession(reg_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def reg_data(reg_session):
    """Create test data for registration E2E tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"eureg-e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="EU Reg Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    reg_session.add(user)
    await reg_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="EU Reg E2E School",
        type="school",
        owner_id=user.id,
    )
    reg_session.add(group)
    await reg_session.flush()

    return {"user": user, "group": group}


@pytest.fixture
async def reg_client(reg_engine, reg_session, reg_data):
    """HTTP client authenticated for registration E2E tests."""
    app = create_app()

    async def get_db_override():
        try:
            yield reg_session
            await reg_session.commit()
        except Exception:
            await reg_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=reg_data["user"].id,
            group_id=reg_data["group"].id,
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


async def _create_approved_assessment(client, group_id: str):
    """Helper: create an assessment and approve it via the full workflow."""
    # Create assessment
    resp = await client.post(
        "/api/v1/governance/eu-ai-act/assessment",
        json={"group_id": group_id, "assessor": "Registration Tester"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _setup_approved_assessment(session, group_id):
    """Helper: create an approved conformity assessment directly in DB."""
    assessment = await create_conformity_assessment(
        session, group_id=group_id, assessor="Registration Tester",
    )
    assessment_id = uuid.UUID(assessment["assessment_id"])
    # Transition draft -> submitted -> approved
    await update_assessment_status(session, assessment_id, "submitted")
    await update_assessment_status(session, assessment_id, "approved")
    await session.commit()
    return assessment


async def _setup_tech_docs(session, group_id):
    """Helper: create technical documentation directly in DB."""
    doc = await generate_tech_documentation(
        session,
        group_id=group_id,
        system_name="Safety Monitor",
        system_description="AI usage monitoring system for child safety",
    )
    await session.commit()
    return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_registration_payload(reg_client, reg_session, reg_data):
    """Generate payload with all required fields after conformity assessment approved."""
    group_id = str(reg_data["group"].id)

    # Setup: create approved assessment + tech docs
    await _setup_approved_assessment(reg_session, group_id)
    await _setup_tech_docs(reg_session, group_id)

    # Generate registration payload
    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["group_id"] == group_id
    assert "registration_id" in data
    assert "payload" in data
    assert "required_fields" in data

    # Payload should contain all required field keys
    payload = data["payload"]
    for field in REGISTRATION_REQUIRED_FIELDS:
        assert field in payload, f"Missing required field: {field}"

    # Conformity assessment ID should be populated
    assert payload["conformity_assessment_id"] is not None
    assert payload["conformity_assessment_status"] == "approved"


@pytest.mark.asyncio
async def test_validate_registration_payload(reg_client, reg_session, reg_data):
    """All required fields must be present and the payload structure is correct."""
    group_id = str(reg_data["group"].id)

    await _setup_approved_assessment(reg_session, group_id)
    await _setup_tech_docs(reg_session, group_id)

    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify required_fields list matches the known set
    assert set(data["required_fields"]) == set(REGISTRATION_REQUIRED_FIELDS)

    # Verify payload has conformity and tech doc references
    payload = data["payload"]
    assert payload["risk_classification"] == "high"
    assert payload["conformity_assessment_version"] >= 1
    assert payload["technical_documentation_id"] is not None
    assert "eu_ai_act_articles" in payload
    assert len(payload["eu_ai_act_articles"]) == 7  # Articles 9-15

    # system_description should be pre-populated from tech docs
    assert len(payload["system_description"]) > 0


@pytest.mark.asyncio
async def test_submit_registration(reg_client, reg_session, reg_data):
    """Submit registration with all required fields populated -> track status."""
    group_id = str(reg_data["group"].id)

    await _setup_approved_assessment(reg_session, group_id)
    await _setup_tech_docs(reg_session, group_id)

    # Generate payload first
    gen_resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert gen_resp.status_code == 200
    reg_id = gen_resp.json()["registration_id"]

    # Manually populate required fields on the draft registration
    from sqlalchemy import select
    result = await reg_session.execute(
        select(RegistrationSubmission).where(
            RegistrationSubmission.id == uuid.UUID(reg_id),
        )
    )
    reg = result.scalars().first()
    assert reg is not None
    reg.payload = {
        **reg.payload,
        "provider_name": "Bhapi Inc",
        "provider_address": "123 Safety St, Dublin, Ireland",
        "system_name": "Bhapi AI Safety Monitor",
        "system_description": "AI usage monitoring for child safety",
        "intended_purpose": "Monitor and govern children's AI interactions",
        "member_state": "Ireland",
        "contact_email": "compliance@bhapi.ai",
    }
    await reg_session.commit()

    # Submit
    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/submit",
        json={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["registration_id"] == reg_id
    assert data["submitted_at"] is not None
    assert "message" in data


@pytest.mark.asyncio
async def test_get_registration_status(reg_client, reg_session, reg_data):
    """Track submission state through the lifecycle."""
    group_id = str(reg_data["group"].id)

    # Initially no registration
    resp = await reg_client.get(
        "/api/v1/governance/eu-ai-act/registration/status",
        params={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_started"
    assert data["registration_id"] is None

    # Generate a draft
    await _setup_approved_assessment(reg_session, group_id)
    await _setup_tech_docs(reg_session, group_id)

    gen_resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert gen_resp.status_code == 200

    # Check status is now draft
    resp = await reg_client.get(
        "/api/v1/governance/eu-ai-act/registration/status",
        params={"group_id": group_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["registration_id"] is not None
    assert data["payload"] is not None


@pytest.mark.asyncio
async def test_registration_requires_conformity_assessment(reg_client, reg_data):
    """Cannot register without an approved conformity assessment."""
    group_id = str(reg_data["group"].id)

    # Try to generate without any assessment
    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert resp.status_code == 422
    assert "conformity assessment" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_registration_missing_fields_rejected(
    reg_client, reg_session, reg_data,
):
    """Submit with missing required fields returns 422."""
    group_id = str(reg_data["group"].id)

    await _setup_approved_assessment(reg_session, group_id)
    await _setup_tech_docs(reg_session, group_id)

    # Generate payload (fields like provider_name are empty strings)
    gen_resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert gen_resp.status_code == 200

    # Try to submit without populating required fields
    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/submit",
        json={"group_id": group_id},
    )
    assert resp.status_code == 422
    assert "missing required fields" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_registration_requires_auth(reg_engine, reg_session):
    """Registration endpoints require authentication."""
    app = create_app()

    async def get_db_override():
        try:
            yield reg_session
            await reg_session.commit()
        except Exception:
            await reg_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        gid = str(uuid.uuid4())

        resp = await client.post(
            "/api/v1/governance/eu-ai-act/registration/generate",
            json={"group_id": gid},
        )
        assert resp.status_code == 401

        resp = await client.post(
            "/api/v1/governance/eu-ai-act/registration/submit",
            json={"group_id": gid},
        )
        assert resp.status_code == 401

        resp = await client.get(
            "/api/v1/governance/eu-ai-act/registration/status",
            params={"group_id": gid},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_registration_draft_not_approved_assessment(
    reg_client, reg_session, reg_data,
):
    """Cannot generate registration if assessment is draft (not approved)."""
    group_id = str(reg_data["group"].id)

    # Create assessment but leave it as draft
    await create_conformity_assessment(
        reg_session, group_id=group_id, assessor="Draft Tester",
    )
    await reg_session.commit()

    resp = await reg_client.post(
        "/api/v1/governance/eu-ai-act/registration/generate",
        json={"group_id": group_id},
    )
    assert resp.status_code == 422
    assert "conformity assessment" in resp.json()["detail"].lower()
