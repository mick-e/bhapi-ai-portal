"""Unit tests for Ohio governance extensions — district customization, CSV import, board report."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.governance.ohio import (
    customize_ohio_policy,
    generate_board_report,
    get_ohio_compliance_status,
    import_tools_csv,
)
from src.governance.service import (
    add_tool_to_inventory,
    create_policy,
)
from tests.conftest import make_test_group


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as s:
        yield s


@pytest_asyncio.fixture
async def school_and_user(session):
    """Create a school group and owner user."""
    group, owner_id = await make_test_group(session, name="Test School", group_type="school")
    return group.id, owner_id


# ---------------------------------------------------------------------------
# customize_ohio_policy
# ---------------------------------------------------------------------------


class TestCustomizeOhioPolicy:
    @pytest.mark.asyncio
    async def test_basic_customization(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Columbus City Schools",
            additional_requirements=["Require parental opt-in for AI tools"],
            approved_tools=["Google Classroom AI", "Khan Academy"],
            actor_id=actor_id,
        )
        assert policy["state_code"] == "OH"
        assert "Columbus City Schools" in policy["content"]["district_name"]
        assert len(policy["content"]["approved_tools"]) == 2

    @pytest.mark.asyncio
    async def test_customization_creates_active_policy(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Cleveland Schools",
            actor_id=actor_id,
        )
        assert policy["status"] == "active"
        assert policy["version"] == 1

    @pytest.mark.asyncio
    async def test_customization_with_no_tools(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Akron Schools",
            actor_id=actor_id,
        )
        assert policy["content"]["approved_tools"] == []

    @pytest.mark.asyncio
    async def test_customization_preserves_requirements(self, session, school_and_user):
        school_id, actor_id = school_and_user
        reqs = ["No AI for grading", "Annual AI ethics training"]
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Dayton Schools",
            additional_requirements=reqs,
            actor_id=actor_id,
        )
        assert policy["content"]["additional_requirements"] == reqs

    @pytest.mark.asyncio
    async def test_customization_with_string_school_id(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await customize_ohio_policy(
            db=session,
            school_id=str(school_id),
            district_name="Cincinnati Schools",
            actor_id=actor_id,
        )
        assert policy["state_code"] == "OH"

    @pytest.mark.asyncio
    async def test_customization_empty_district_name_fails(self, session, school_and_user):
        school_id, actor_id = school_and_user
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="district_name"):
            await customize_ohio_policy(
                db=session,
                school_id=school_id,
                district_name="",
                actor_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_customization_whitespace_district_name_fails(self, session, school_and_user):
        school_id, actor_id = school_and_user
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="district_name"):
            await customize_ohio_policy(
                db=session,
                school_id=school_id,
                district_name="   ",
                actor_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_customization_returns_policy_id(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Toledo Schools",
            actor_id=actor_id,
        )
        assert "policy_id" in policy
        assert len(policy["policy_id"]) > 0

    @pytest.mark.asyncio
    async def test_customization_creates_audit_entry(self, session, school_and_user):
        school_id, actor_id = school_and_user
        from src.governance.service import get_audit_trail
        policy = await customize_ohio_policy(
            db=session,
            school_id=school_id,
            district_name="Springfield Schools",
            actor_id=actor_id,
        )
        audits = await get_audit_trail(session, uuid.UUID(policy["policy_id"]))
        assert audits.total == 1
        assert audits.items[0].action == "ohio_customized"


# ---------------------------------------------------------------------------
# import_tools_csv
# ---------------------------------------------------------------------------


class TestImportToolsCsv:
    @pytest.mark.asyncio
    async def test_basic_csv_import(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "ChatGPT,OpenAI,high,pending\n"
            "Grammarly,Grammarly Inc,low,approved"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["imported"] == 2
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_csv_import_with_invalid_risk_level(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "BadTool,Corp,extreme,approved"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["row"] == 2

    @pytest.mark.asyncio
    async def test_csv_import_mixed_valid_invalid(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "Good Tool,Vendor,low,approved\n"
            ",Missing,low,approved\n"
            "Another,Corp,medium,pending"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["imported"] == 2
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_csv_import_missing_columns(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = "tool_name,vendor\nTool,Vendor"
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="missing required columns"):
            await import_tools_csv(session, school_id, csv_data, actor_id)

    @pytest.mark.asyncio
    async def test_csv_import_empty_rows(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = "tool_name,vendor,risk_level,approval_status\n"
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["imported"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_csv_import_creates_import_log(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "ChatGPT,OpenAI,high,pending"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert "import_log_id" in result
        assert len(result["import_log_id"]) > 0

    @pytest.mark.asyncio
    async def test_csv_import_total_rows(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "Tool1,V1,low,approved\n"
            "Tool2,V2,medium,pending\n"
            "Tool3,V3,high,denied"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["total_rows"] == 3
        assert result["imported"] == 3

    @pytest.mark.asyncio
    async def test_csv_import_invalid_approval_status(self, session, school_and_user):
        school_id, actor_id = school_and_user
        csv_data = (
            "tool_name,vendor,risk_level,approval_status\n"
            "Tool,Vendor,low,maybe"
        )
        result = await import_tools_csv(session, school_id, csv_data, actor_id)
        assert result["imported"] == 0
        assert len(result["errors"]) == 1


# ---------------------------------------------------------------------------
# generate_board_report
# ---------------------------------------------------------------------------


class TestGenerateBoardReport:
    @pytest.mark.asyncio
    async def test_basic_board_report(self, session, school_and_user):
        school_id, actor_id = school_and_user
        report = await generate_board_report(session, school_id)
        assert report["format"] == "pdf"
        assert "compliance_score" in report
        assert "tool_inventory_count" in report

    @pytest.mark.asyncio
    async def test_board_report_with_policies(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        await create_policy(session, school_id, "OH", "governance", {}, actor_id)
        report = await generate_board_report(session, school_id)
        assert report["policy_count"] == 2
        assert "ai_usage" in report["policy_coverage"]

    @pytest.mark.asyncio
    async def test_board_report_with_tools(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await add_tool_to_inventory(session, school_id, "ChatGPT", "OpenAI", "high", "approved", actor_id)
        await add_tool_to_inventory(session, school_id, "Gemini", "Google", "low", "pending", actor_id)
        report = await generate_board_report(session, school_id)
        assert report["tool_inventory_count"] == 2
        assert report["tools_by_risk"]["high"] == 1
        assert report["tools_by_risk"]["low"] == 1

    @pytest.mark.asyncio
    async def test_board_report_compliance_score(self, session, school_and_user):
        school_id, actor_id = school_and_user
        for pt in ["ai_usage", "risk_assessment", "governance"]:
            await create_policy(session, school_id, "OH", pt, {}, actor_id)
        report = await generate_board_report(session, school_id)
        assert report["compliance_score"] == 100
        assert report["is_compliant"] is True

    @pytest.mark.asyncio
    async def test_board_report_non_compliant(self, session, school_and_user):
        school_id, _ = school_and_user
        report = await generate_board_report(session, school_id)
        assert report["compliance_score"] < 100
        assert len(report["missing_policies"]) > 0

    @pytest.mark.asyncio
    async def test_board_report_includes_risk_findings(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await add_tool_to_inventory(session, school_id, "Risky", "Corp", "high", "pending", actor_id)
        report = await generate_board_report(session, school_id)
        assert len(report["risk_findings"]) > 0

    @pytest.mark.asyncio
    async def test_board_report_district_name(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await customize_ohio_policy(
            session, school_id, "Columbus City Schools", actor_id=actor_id,
        )
        report = await generate_board_report(session, school_id)
        assert report["district_name"] == "Columbus City Schools"

    @pytest.mark.asyncio
    async def test_board_report_state_code(self, session, school_and_user):
        school_id, _ = school_and_user
        report = await generate_board_report(session, school_id)
        assert report["state_code"] == "OH"


# ---------------------------------------------------------------------------
# get_ohio_compliance_status
# ---------------------------------------------------------------------------


class TestOhioComplianceStatus:
    @pytest.mark.asyncio
    async def test_empty_school_non_compliant(self, session, school_and_user):
        school_id, _ = school_and_user
        status = await get_ohio_compliance_status(session, school_id)
        assert status["overall_status"] == "non_compliant"
        assert status["state_code"] == "OH"
        assert status["ready_for_board"] is False

    @pytest.mark.asyncio
    async def test_fully_compliant(self, session, school_and_user):
        school_id, actor_id = school_and_user
        # Create all required policies as active
        for pt in ["ai_usage", "risk_assessment", "governance"]:
            from src.governance.models import GovernancePolicy
            from uuid import uuid4
            policy = GovernancePolicy(
                id=uuid4(), school_id=school_id, state_code="OH",
                policy_type=pt, content={}, status="active", version=1,
            )
            session.add(policy)
        # Add a tool
        await add_tool_to_inventory(session, school_id, "Tool", "V", "low", "approved", actor_id)
        await session.flush()

        status = await get_ohio_compliance_status(session, school_id)
        assert status["overall_status"] == "compliant"
        assert status["ready_for_board"] is True

    @pytest.mark.asyncio
    async def test_compliance_deadline(self, session, school_and_user):
        school_id, _ = school_and_user
        status = await get_ohio_compliance_status(session, school_id)
        assert status["compliance_deadline"] == "2026-07-01"

    @pytest.mark.asyncio
    async def test_policy_status_detail(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        status = await get_ohio_compliance_status(session, school_id)
        assert status["policy_status"]["ai_usage"]["exists"] is True
        # draft_only because create_policy sets status=draft
        assert status["policy_status"]["ai_usage"]["status"] == "draft_only"

    @pytest.mark.asyncio
    async def test_missing_policy_detail(self, session, school_and_user):
        school_id, _ = school_and_user
        status = await get_ohio_compliance_status(session, school_id)
        assert status["policy_status"]["governance"]["exists"] is False
        assert status["policy_status"]["governance"]["status"] == "missing"

    @pytest.mark.asyncio
    async def test_tool_count_in_status(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await add_tool_to_inventory(session, school_id, "T1", "V1", "low", "approved", actor_id)
        await add_tool_to_inventory(session, school_id, "T2", "V2", "low", "approved", actor_id)
        status = await get_ohio_compliance_status(session, school_id)
        assert status["tool_count"] == 2

    @pytest.mark.asyncio
    async def test_string_school_id(self, session, school_and_user):
        school_id, _ = school_and_user
        status = await get_ohio_compliance_status(session, str(school_id))
        assert status["state_code"] == "OH"
