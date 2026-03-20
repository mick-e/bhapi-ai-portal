"""End-to-end tests for Ohio governance extensions — HTTP endpoint tests."""

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
        email=f"ohio-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Ohio Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=school_id,
        name="Columbus City Schools",
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
# Ohio Customize Endpoint
# ---------------------------------------------------------------------------


class TestOhioCustomizeEndpoint:
    @pytest.mark.asyncio
    async def test_customize_ohio_policy(self, client, school_id):
        resp = await client.post("/api/v1/governance/ohio/customize", json={
            "school_id": str(school_id),
            "district_name": "Columbus City Schools",
            "additional_requirements": ["Parental opt-in required"],
            "approved_tools": ["Google Classroom AI", "Khan Academy"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["state_code"] == "OH"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_customize_with_no_extras(self, client, school_id):
        resp = await client.post("/api/v1/governance/ohio/customize", json={
            "school_id": str(school_id),
            "district_name": "Akron Schools",
        })
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_customize_empty_district_name(self, client, school_id):
        resp = await client.post("/api/v1/governance/ohio/customize", json={
            "school_id": str(school_id),
            "district_name": "",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Ohio Import Tools Endpoint
# ---------------------------------------------------------------------------


class TestOhioImportToolsEndpoint:
    @pytest.mark.asyncio
    async def test_import_tools_csv(self, client, school_id):
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "ChatGPT,OpenAI,high,pending\n"
            "Grammarly,Grammarly Inc,low,approved"
        )
        resp = await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id),
            "csv_data": csv_data,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_import_tools_with_errors(self, client, school_id):
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "Good,Vendor,low,approved\n"
            "Bad,,extreme,maybe"
        )
        resp = await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id),
            "csv_data": csv_data,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert len(data["errors"]) == 1

    @pytest.mark.asyncio
    async def test_import_tools_missing_columns(self, client, school_id):
        csv_data = "tool_name,vendor\nTool,Vendor"
        resp = await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id),
            "csv_data": csv_data,
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Ohio Board Report Endpoint
# ---------------------------------------------------------------------------


class TestOhioBoardReportEndpoint:
    @pytest.mark.asyncio
    async def test_board_report_empty(self, client, school_id):
        resp = await client.get(
            "/api/v1/governance/ohio/board-report",
            params={"school_id": str(school_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "pdf"
        assert "compliance_score" in data
        assert "tool_inventory_count" in data

    @pytest.mark.asyncio
    async def test_board_report_with_policies_and_tools(self, client, school_id):
        # Create policies
        for pt in ["ai_usage", "risk_assessment", "governance"]:
            await client.post("/api/v1/governance/policies", json={
                "school_id": str(school_id), "state_code": "OH",
                "policy_type": pt, "content": {},
            })
        # Add tools
        await client.post("/api/v1/governance/tools", json={
            "school_id": str(school_id), "tool_name": "ChatGPT",
            "vendor": "OpenAI", "risk_level": "high", "approval_status": "approved",
        })
        resp = await client.get(
            "/api/v1/governance/ohio/board-report",
            params={"school_id": str(school_id)},
        )
        data = resp.json()
        assert data["policy_count"] == 3
        assert data["tool_inventory_count"] == 1


# ---------------------------------------------------------------------------
# Ohio Status Endpoint
# ---------------------------------------------------------------------------


class TestOhioStatusEndpoint:
    @pytest.mark.asyncio
    async def test_status_empty(self, client, school_id):
        resp = await client.get(
            "/api/v1/governance/ohio/status",
            params={"school_id": str(school_id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "non_compliant"
        assert data["compliance_deadline"] == "2026-07-01"

    @pytest.mark.asyncio
    async def test_status_with_policies(self, client, school_id):
        await client.post("/api/v1/governance/policies", json={
            "school_id": str(school_id), "state_code": "OH",
            "policy_type": "ai_usage", "content": {},
        })
        resp = await client.get(
            "/api/v1/governance/ohio/status",
            params={"school_id": str(school_id)},
        )
        data = resp.json()
        assert data["policy_status"]["ai_usage"]["exists"] is True


# ---------------------------------------------------------------------------
# Full Ohio Workflow
# ---------------------------------------------------------------------------


class TestOhioFullWorkflow:
    @pytest.mark.asyncio
    async def test_full_ohio_workflow(self, client, school_id):
        """Complete flow: customize -> import tools -> check status -> board report."""
        # Step 1: Customize Ohio policy
        customize_resp = await client.post("/api/v1/governance/ohio/customize", json={
            "school_id": str(school_id),
            "district_name": "Columbus City Schools",
            "additional_requirements": ["Annual AI training", "Parental opt-in"],
            "approved_tools": ["Google Classroom AI"],
        })
        assert customize_resp.status_code == 201

        # Step 2: Import tools via CSV
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "ChatGPT,OpenAI,high,approved\n"
            "Grammarly,Grammarly Inc,low,approved\n"
            "Copilot,Microsoft,medium,pending"
        )
        import_resp = await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id),
            "csv_data": csv_data,
        })
        assert import_resp.status_code == 200
        assert import_resp.json()["imported"] == 3

        # Step 3: Add remaining required policies
        for pt in ["risk_assessment", "governance"]:
            await client.post("/api/v1/governance/policies", json={
                "school_id": str(school_id), "state_code": "OH",
                "policy_type": pt, "content": {},
            })

        # Step 4: Check compliance status
        status_resp = await client.get(
            "/api/v1/governance/ohio/status",
            params={"school_id": str(school_id)},
        )
        assert status_resp.status_code == 200

        # Step 5: Generate board report
        report_resp = await client.get(
            "/api/v1/governance/ohio/board-report",
            params={"school_id": str(school_id)},
        )
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert report["format"] == "pdf"
        assert report["tool_inventory_count"] >= 3
        assert report["district_name"] == "Columbus City Schools"

    @pytest.mark.asyncio
    async def test_import_then_verify_tools_listed(self, client, school_id):
        """Import tools via CSV, then verify they appear in tool listing."""
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "Tool1,Vendor1,low,approved\n"
            "Tool2,Vendor2,medium,pending"
        )
        await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id),
            "csv_data": csv_data,
        })
        tools_resp = await client.get(
            "/api/v1/governance/tools",
            params={"school_id": str(school_id)},
        )
        assert len(tools_resp.json()) == 2

    @pytest.mark.asyncio
    async def test_customize_then_board_report_shows_district(self, client, school_id):
        """Customize with district name, then verify board report includes it."""
        await client.post("/api/v1/governance/ohio/customize", json={
            "school_id": str(school_id),
            "district_name": "Dayton Public Schools",
        })
        report = await client.get(
            "/api/v1/governance/ohio/board-report",
            params={"school_id": str(school_id)},
        )
        assert report.json()["district_name"] == "Dayton Public Schools"

    @pytest.mark.asyncio
    async def test_multiple_imports_accumulate(self, client, school_id):
        """Multiple CSV imports should accumulate tools."""
        csv1 = "tool_name,vendor,risk_level,approval_status\nT1,V1,low,approved"
        csv2 = "tool_name,vendor,risk_level,approval_status\nT2,V2,medium,pending"
        await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id), "csv_data": csv1,
        })
        await client.post("/api/v1/governance/ohio/import-tools", json={
            "school_id": str(school_id), "csv_data": csv2,
        })
        tools = await client.get(
            "/api/v1/governance/tools", params={"school_id": str(school_id)},
        )
        assert len(tools.json()) == 2
