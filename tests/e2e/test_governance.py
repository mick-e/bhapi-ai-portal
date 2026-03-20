"""End-to-end tests for the governance module — HTTP endpoint tests."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
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


@pytest_asyncio.fixture
async def e2e_engine():
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


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    """Create a user and school group."""
    user_id = uuid.uuid4()
    school_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"gov-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Gov Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=school_id,
        name="Test School",
        type="school",
        owner_id=user_id,
        settings={},
    )
    e2e_session.add(group)
    await e2e_session.flush()

    return {"user_id": user_id, "school_id": school_id}


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
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
            user_id=user_id,
            group_id=group_id,
            role="admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def client(e2e_engine, e2e_session, e2e_data):
    async with _make_client(
        e2e_engine, e2e_session, e2e_data["user_id"], e2e_data["school_id"],
    ) as c:
        yield c


@pytest_asyncio.fixture
def school_id(e2e_data):
    return e2e_data["school_id"]


# ---------------------------------------------------------------------------
# Policy CRUD E2E
# ---------------------------------------------------------------------------


class TestPolicyEndpoints:
    @pytest.mark.asyncio
    async def test_create_policy(self, client, school_id):
        resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id),
            "state_code": "OH",
            "policy_type": "ai_usage",
            "content": {"title": "AI Usage Policy"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["policy_type"] == "ai_usage"
        assert data["status"] == "draft"
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_list_policies(self, client, school_id):
        # Create two policies
        await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "governance", "content": {},
        })
        resp = await client.get(
            "/api/v1/governance/policies", params={"school_id": str(school_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_get_policy(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {"x": 1},
        })
        pid = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/governance/policies/{pid}")
        assert resp.status_code == 200
        assert resp.json()["content"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_get_nonexistent_policy(self, client):
        resp = await client.get(f"/api/v1/governance/policies/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_policy(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {"v": 1},
        })
        pid = create_resp.json()["id"]
        resp = await client.put(f"/api/v1/governance/policies/{pid}", json={
            "content": {"v": 2},
        })
        assert resp.status_code == 200
        assert resp.json()["version"] == 2
        assert resp.json()["content"] == {"v": 2}

    @pytest.mark.asyncio
    async def test_archive_policy(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        pid = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/governance/policies/{pid}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    @pytest.mark.asyncio
    async def test_archive_already_archived(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        pid = create_resp.json()["id"]
        await client.patch(f"/api/v1/governance/policies/{pid}/archive")
        resp = await client.patch(f"/api/v1/governance/policies/{pid}/archive")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_policies_with_status_filter(self, client, school_id):
        await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        resp = await client.get(
            "/api/v1/governance/policies",
            params={"school_id": str(school_id), "status": "draft"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_policies_pagination(self, client, school_id):
        for _ in range(5):
            await client.post("/api/v1/governance/policies", json={
                "school_id": str(school_id), "state_code": "OH",
                "policy_type": "ai_usage", "content": {},
            })
        resp = await client.get(
            "/api/v1/governance/policies",
            params={"school_id": str(school_id), "page": 1, "page_size": 2},
        )
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Template E2E
# ---------------------------------------------------------------------------


class TestTemplateEndpoints:
    @pytest.mark.asyncio
    async def test_generate_ohio_ai_usage(self, client):
        resp = await client.post("/api/v1/governance/templates/generate", json={
            "state_code": "OH", "policy_type": "ai_usage",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["state_code"] == "OH"
        assert "purpose_statement" in data["template"]
        assert "incident_response" in data["template"]

    @pytest.mark.asyncio
    async def test_generate_generic_template(self, client):
        resp = await client.post("/api/v1/governance/templates/generate", json={
            "state_code": "CA", "policy_type": "ai_usage",
        })
        assert resp.status_code == 200
        assert "sections" in resp.json()["template"]

    @pytest.mark.asyncio
    async def test_generate_ohio_governance(self, client):
        resp = await client.post("/api/v1/governance/templates/generate", json={
            "state_code": "OH", "policy_type": "governance",
        })
        assert resp.status_code == 200
        assert "roles" in resp.json()["template"]


# ---------------------------------------------------------------------------
# Tool inventory E2E
# ---------------------------------------------------------------------------


class TestToolEndpoints:
    @pytest.mark.asyncio
    async def test_add_tool(self, client, school_id):
        resp = await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id),
            "tool_name": "ChatGPT",
            "vendor": "OpenAI",
            "risk_level": "medium",
            "approval_status": "approved",
        })
        assert resp.status_code == 201
        assert resp.json()["tool_name"] == "ChatGPT"

    @pytest.mark.asyncio
    async def test_list_tools(self, client, school_id):
        await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id),
            "tool_name": "ChatGPT", "vendor": "OpenAI",
            "risk_level": "low", "approval_status": "approved",
        })
        resp = await client.get(
            "/api/v1/governance/tools", params={"school_id": str(school_id)},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_add_tool_invalid_risk(self, client, school_id):
        resp = await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id),
            "tool_name": "T", "vendor": "V",
            "risk_level": "extreme", "approval_status": "approved",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Risk assessment E2E
# ---------------------------------------------------------------------------


class TestRiskAssessmentEndpoints:
    @pytest.mark.asyncio
    async def test_risk_assessment(self, client, school_id):
        resp = await client.post("/api/v1/governance/risk-assessment", json={
            "school_id": str(school_id),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "findings" in data

    @pytest.mark.asyncio
    async def test_risk_assessment_perfect_score(self, client, school_id):
        for pt in ["ai_usage", "risk_assessment", "governance"]:
            await client.post("/api/v1/governance/policies", json={
                "school_id": str(school_id), "state_code": "OH",
                "policy_type": pt, "content": {},
            })
        resp = await client.post("/api/v1/governance/risk-assessment", json={
            "school_id": str(school_id),
        })
        assert resp.json()["score"] == 100


# ---------------------------------------------------------------------------
# Dashboard E2E
# ---------------------------------------------------------------------------


class TestDashboardEndpoints:
    @pytest.mark.asyncio
    async def test_dashboard_empty(self, client, school_id):
        resp = await client.get(
            "/api/v1/governance/dashboard", params={"school_id": str(school_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_count"] == 0
        assert data["tool_count"] == 0
        assert len(data["missing_policies"]) == 3

    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, client, school_id):
        await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id), "tool_name": "GPT",
            "vendor": "OpenAI", "risk_level": "low", "approval_status": "approved",
        })
        resp = await client.get(
            "/api/v1/governance/dashboard", params={"school_id": str(school_id)},
        )
        data = resp.json()
        assert data["policy_count"] == 1
        assert data["tool_count"] == 1
        assert "ai_usage" in data["policy_coverage"]


# ---------------------------------------------------------------------------
# Audit E2E
# ---------------------------------------------------------------------------


class TestAuditEndpoints:
    @pytest.mark.asyncio
    async def test_audit_trail(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {"v": 1},
        })
        pid = create_resp.json()["id"]
        await client.put(f"/api/v1/governance/policies/{pid}", json={
            "content": {"v": 2},
        })
        resp = await client.get(f"/api/v1/governance/audits/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_audit_trail_nonexistent(self, client):
        resp = await client.get(f"/api/v1/governance/audits/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_trail_after_archive(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        pid = create_resp.json()["id"]
        await client.patch(f"/api/v1/governance/policies/{pid}/archive")
        resp = await client.get(f"/api/v1/governance/audits/{pid}")
        assert resp.status_code == 200
        actions = {a["action"] for a in resp.json()["items"]}
        assert "archived" in actions

    @pytest.mark.asyncio
    async def test_audit_pagination(self, client, school_id):
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {"v": 1},
        })
        pid = create_resp.json()["id"]
        for i in range(4):
            await client.put(f"/api/v1/governance/policies/{pid}", json={
                "content": {"v": i + 2},
            })
        resp = await client.get(
            f"/api/v1/governance/audits/{pid}",
            params={"page": 1, "page_size": 2},
        )
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Full workflow E2E
# ---------------------------------------------------------------------------


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_full_governance_workflow(self, client, school_id):
        """Test complete workflow: template -> create -> update -> archive."""
        # Generate template
        tmpl = await client.post("/api/v1/governance/templates/generate", json={
            "state_code": "OH", "policy_type": "ai_usage",
        })
        assert tmpl.status_code == 200

        # Create policy from template
        create_resp = await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": tmpl.json()["template"],
        })
        assert create_resp.status_code == 201
        pid = create_resp.json()["id"]

        # Update
        upd = await client.put(f"/api/v1/governance/policies/{pid}", json={
            "content": {"updated": True},
        })
        assert upd.status_code == 200
        assert upd.json()["version"] == 2

        # Archive
        arch = await client.patch(f"/api/v1/governance/policies/{pid}/archive")
        assert arch.status_code == 200
        assert arch.json()["status"] == "archived"

        # Verify audit trail
        audits = await client.get(f"/api/v1/governance/audits/{pid}")
        assert audits.json()["total"] == 3

    @pytest.mark.asyncio
    async def test_tool_and_risk_workflow(self, client, school_id):
        """Add tools, run risk assessment, check dashboard."""
        # Add tool
        await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id), "tool_name": "ChatGPT",
            "vendor": "OpenAI", "risk_level": "high", "approval_status": "pending",
        })

        # Risk assessment (should penalize high-risk unapproved)
        risk = await client.post("/api/v1/governance/risk-assessment", json={
            "school_id": str(school_id),
        })
        assert risk.json()["score"] < 100
        assert len(risk.json()["findings"]) > 0

        # Dashboard
        dash = await client.get(
            "/api/v1/governance/dashboard", params={"school_id": str(school_id)},
        )
        assert dash.json()["tool_count"] == 1

    @pytest.mark.asyncio
    async def test_update_nonexistent_policy(self, client):
        resp = await client.put(f"/api/v1/governance/policies/{uuid.uuid4()}", json={
            "content": {"v": 1},
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_archive_nonexistent_policy(self, client):
        resp = await client.patch(f"/api/v1/governance/policies/{uuid.uuid4()}/archive")
        assert resp.status_code == 404
