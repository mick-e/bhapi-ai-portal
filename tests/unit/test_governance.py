"""Unit tests for the governance module — service layer tests."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.governance.models import GovernanceAudit, GovernancePolicy
from src.governance.service import (
    REQUIRED_POLICY_TYPES,
    add_tool_to_inventory,
    archive_policy,
    create_policy,
    generate_template,
    get_audit_trail,
    get_compliance_dashboard,
    get_policy,
    list_policies,
    list_tool_inventory,
    run_risk_assessment,
    update_policy,
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
# create_policy
# ---------------------------------------------------------------------------


class TestCreatePolicy:
    @pytest.mark.asyncio
    async def test_create_policy_basic(self, session, school_and_user):
        school_id, actor_id = school_and_user
        result = await create_policy(
            session, school_id, "OH", "ai_usage", {"title": "Test"}, actor_id,
        )
        assert result.school_id == school_id
        assert result.state_code == "OH"
        assert result.policy_type == "ai_usage"
        assert result.status == "draft"
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_create_policy_creates_audit(self, session, school_and_user):
        school_id, actor_id = school_and_user
        result = await create_policy(
            session, school_id, "OH", "ai_usage", {"title": "Test"}, actor_id,
        )
        audits = await get_audit_trail(session, result.id)
        assert audits.total == 1
        assert audits.items[0].action == "created"
        assert audits.items[0].actor_id == actor_id

    @pytest.mark.asyncio
    async def test_create_policy_content_preserved(self, session, school_and_user):
        school_id, actor_id = school_and_user
        content = {"title": "My Policy", "sections": ["a", "b"]}
        result = await create_policy(
            session, school_id, "OH", "governance", content, actor_id,
        )
        assert result.content == content

    @pytest.mark.asyncio
    async def test_create_multiple_policies(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        await create_policy(session, school_id, "OH", "governance", {}, actor_id)
        policies = await list_policies(session, school_id)
        assert policies.total == 2


# ---------------------------------------------------------------------------
# update_policy
# ---------------------------------------------------------------------------


class TestUpdatePolicy:
    @pytest.mark.asyncio
    async def test_update_policy_content(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {"v": 1}, actor_id,
        )
        updated = await update_policy(session, policy.id, {"v": 2}, actor_id)
        assert updated.content == {"v": 2}
        assert updated.version == 2

    @pytest.mark.asyncio
    async def test_update_policy_creates_audit_with_diff(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {"v": 1}, actor_id,
        )
        await update_policy(session, policy.id, {"v": 2}, actor_id)
        audits = await get_audit_trail(session, policy.id)
        assert audits.total == 2
        actions = {a.action for a in audits.items}
        assert "updated" in actions
        update_audit = next(a for a in audits.items if a.action == "updated")
        assert update_audit.diff == {"old": {"v": 1}, "new": {"v": 2}}

    @pytest.mark.asyncio
    async def test_update_archived_policy_fails(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {"v": 1}, actor_id,
        )
        await archive_policy(session, policy.id, actor_id)
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="archived"):
            await update_policy(session, policy.id, {"v": 2}, actor_id)

    @pytest.mark.asyncio
    async def test_update_nonexistent_policy(self, session):
        from src.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await update_policy(session, uuid.uuid4(), {}, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_update_increments_version(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {"v": 1}, actor_id,
        )
        updated1 = await update_policy(session, policy.id, {"v": 2}, actor_id)
        updated2 = await update_policy(session, updated1.id, {"v": 3}, actor_id)
        assert updated2.version == 3


# ---------------------------------------------------------------------------
# get_policy
# ---------------------------------------------------------------------------


class TestGetPolicy:
    @pytest.mark.asyncio
    async def test_get_policy(self, session, school_and_user):
        school_id, actor_id = school_and_user
        created = await create_policy(
            session, school_id, "OH", "ai_usage", {"x": 1}, actor_id,
        )
        fetched = await get_policy(session, created.id)
        assert fetched.id == created.id
        assert fetched.content == {"x": 1}

    @pytest.mark.asyncio
    async def test_get_nonexistent_policy(self, session):
        from src.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await get_policy(session, uuid.uuid4())


# ---------------------------------------------------------------------------
# list_policies
# ---------------------------------------------------------------------------


class TestListPolicies:
    @pytest.mark.asyncio
    async def test_list_empty(self, session, school_and_user):
        school_id, _ = school_and_user
        result = await list_policies(session, school_id)
        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        p2 = await create_policy(session, school_id, "OH", "governance", {}, actor_id)
        await archive_policy(session, p2.id, actor_id)
        result = await list_policies(session, school_id, status="draft")
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        await create_policy(session, school_id, "OH", "governance", {}, actor_id)
        result = await list_policies(session, school_id, policy_type="ai_usage")
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_pagination(self, session, school_and_user):
        school_id, actor_id = school_and_user
        for i in range(5):
            await create_policy(session, school_id, "OH", "ai_usage", {"i": i}, actor_id)
        result = await list_policies(session, school_id, page=1, page_size=2)
        assert result.total == 5
        assert len(result.items) == 2
        assert result.page == 1

    @pytest.mark.asyncio
    async def test_list_page_2(self, session, school_and_user):
        school_id, actor_id = school_and_user
        for i in range(5):
            await create_policy(session, school_id, "OH", "ai_usage", {"i": i}, actor_id)
        result = await list_policies(session, school_id, page=2, page_size=2)
        assert len(result.items) == 2


# ---------------------------------------------------------------------------
# archive_policy
# ---------------------------------------------------------------------------


class TestArchivePolicy:
    @pytest.mark.asyncio
    async def test_archive_policy(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {}, actor_id,
        )
        archived = await archive_policy(session, policy.id, actor_id)
        assert archived.status == "archived"

    @pytest.mark.asyncio
    async def test_archive_already_archived(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {}, actor_id,
        )
        await archive_policy(session, policy.id, actor_id)
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="already archived"):
            await archive_policy(session, policy.id, actor_id)

    @pytest.mark.asyncio
    async def test_archive_creates_audit(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {}, actor_id,
        )
        await archive_policy(session, policy.id, actor_id)
        audits = await get_audit_trail(session, policy.id)
        actions = [a.action for a in audits.items]
        assert "archived" in actions


# ---------------------------------------------------------------------------
# generate_template
# ---------------------------------------------------------------------------


class TestGenerateTemplate:
    def test_ohio_ai_usage_template(self):
        result = generate_template("OH", "ai_usage")
        assert result.state_code == "OH"
        assert result.policy_type == "ai_usage"
        t = result.template
        assert "purpose_statement" in t
        assert "approved_tools" in t
        assert "prohibited_uses" in t
        assert "student_data_protection" in t
        assert "staff_training" in t
        assert "review_schedule" in t
        assert "incident_response" in t

    def test_ohio_tool_inventory_template(self):
        result = generate_template("OH", "tool_inventory")
        assert "fields" in result.template

    def test_ohio_risk_assessment_template(self):
        result = generate_template("OH", "risk_assessment")
        assert "categories" in result.template

    def test_ohio_governance_template(self):
        result = generate_template("OH", "governance")
        assert "roles" in result.template

    def test_generic_template(self):
        result = generate_template("CA", "ai_usage")
        assert "sections" in result.template

    def test_ohio_unknown_type_gets_generic(self):
        result = generate_template("OH", "unknown_type")
        assert "sections" in result.template


# ---------------------------------------------------------------------------
# Tool inventory
# ---------------------------------------------------------------------------


class TestToolInventory:
    @pytest.mark.asyncio
    async def test_add_tool(self, session, school_and_user):
        school_id, actor_id = school_and_user
        tool = await add_tool_to_inventory(
            session, school_id, "ChatGPT", "OpenAI", "medium", "approved", actor_id,
        )
        assert tool.tool_name == "ChatGPT"
        assert tool.vendor == "OpenAI"
        assert tool.risk_level == "medium"
        assert tool.approval_status == "approved"

    @pytest.mark.asyncio
    async def test_add_tool_invalid_risk_level(self, session, school_and_user):
        school_id, actor_id = school_and_user
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="risk_level"):
            await add_tool_to_inventory(
                session, school_id, "Tool", "V", "extreme", "approved", actor_id,
            )

    @pytest.mark.asyncio
    async def test_add_tool_invalid_approval_status(self, session, school_and_user):
        school_id, actor_id = school_and_user
        from src.exceptions import ValidationError
        with pytest.raises(ValidationError, match="approval_status"):
            await add_tool_to_inventory(
                session, school_id, "Tool", "V", "low", "maybe", actor_id,
            )

    @pytest.mark.asyncio
    async def test_list_tools(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await add_tool_to_inventory(
            session, school_id, "ChatGPT", "OpenAI", "medium", "approved", actor_id,
        )
        await add_tool_to_inventory(
            session, school_id, "Gemini", "Google", "low", "approved", actor_id,
        )
        tools = await list_tool_inventory(session, school_id)
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def test_list_tools_empty(self, session, school_and_user):
        school_id, _ = school_and_user
        tools = await list_tool_inventory(session, school_id)
        assert tools == []


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


class TestRiskAssessment:
    @pytest.mark.asyncio
    async def test_risk_score_perfect(self, session, school_and_user):
        """School with all required policies and no tools gets 100."""
        school_id, actor_id = school_and_user
        for pt in REQUIRED_POLICY_TYPES:
            await create_policy(session, school_id, "OH", pt, {}, actor_id)
        result = await run_risk_assessment(session, school_id)
        assert result.score == 100
        assert result.findings == []

    @pytest.mark.asyncio
    async def test_risk_score_missing_all_policies(self, session, school_and_user):
        school_id, _ = school_and_user
        result = await run_risk_assessment(session, school_id)
        # 3 missing required policies: -15 each = -45
        assert result.score == 55
        assert len(result.findings) == 3

    @pytest.mark.asyncio
    async def test_risk_high_risk_unapproved(self, session, school_and_user):
        school_id, actor_id = school_and_user
        for pt in REQUIRED_POLICY_TYPES:
            await create_policy(session, school_id, "OH", pt, {}, actor_id)
        await add_tool_to_inventory(
            session, school_id, "Risky AI", "Corp", "high", "pending", actor_id,
        )
        result = await run_risk_assessment(session, school_id)
        assert result.score == 80  # -20 for high-risk unapproved

    @pytest.mark.asyncio
    async def test_risk_tools_without_ai_usage_policy(self, session, school_and_user):
        school_id, actor_id = school_and_user
        # Only create governance and risk_assessment policies (no ai_usage)
        await create_policy(session, school_id, "OH", "governance", {}, actor_id)
        await create_policy(session, school_id, "OH", "risk_assessment", {}, actor_id)
        await add_tool_to_inventory(
            session, school_id, "Tool1", "V1", "low", "approved", actor_id,
        )
        result = await run_risk_assessment(session, school_id)
        # -15 for missing ai_usage, -10 for tool without ai_usage policy
        assert result.score == 75

    @pytest.mark.asyncio
    async def test_risk_score_clamped_to_zero(self, session, school_and_user):
        """Score doesn't go below 0."""
        school_id, actor_id = school_and_user
        # Add many high-risk unapproved tools
        for i in range(10):
            await add_tool_to_inventory(
                session, school_id, f"Tool{i}", "V", "high", "pending", actor_id,
            )
        result = await run_risk_assessment(session, school_id)
        assert result.score == 0


# ---------------------------------------------------------------------------
# Compliance dashboard
# ---------------------------------------------------------------------------


class TestComplianceDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_empty(self, session, school_and_user):
        school_id, _ = school_and_user
        result = await get_compliance_dashboard(session, school_id)
        assert result.school_id == school_id
        assert result.policy_count == 0
        assert result.tool_count == 0
        assert result.missing_policies == REQUIRED_POLICY_TYPES

    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        await add_tool_to_inventory(
            session, school_id, "ChatGPT", "OpenAI", "low", "approved", actor_id,
        )
        result = await get_compliance_dashboard(session, school_id)
        assert result.policy_count == 1
        assert result.tool_count == 1
        assert "ai_usage" in result.policy_coverage
        assert "ai_usage" not in result.missing_policies

    @pytest.mark.asyncio
    async def test_dashboard_recent_audits(self, session, school_and_user):
        school_id, actor_id = school_and_user
        await create_policy(session, school_id, "OH", "ai_usage", {}, actor_id)
        result = await get_compliance_dashboard(session, school_id)
        assert len(result.recent_audits) >= 1


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_audit_trail_pagination(self, session, school_and_user):
        school_id, actor_id = school_and_user
        policy = await create_policy(
            session, school_id, "OH", "ai_usage", {"v": 1}, actor_id,
        )
        # Create + 3 updates = 4 audits
        for i in range(3):
            await update_policy(session, policy.id, {"v": i + 2}, actor_id)
        result = await get_audit_trail(session, policy.id, page=1, page_size=2)
        assert result.total == 4
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_audit_trail_nonexistent_policy(self, session):
        from src.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await get_audit_trail(session, uuid.uuid4())
