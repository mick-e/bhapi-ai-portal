"""Unit tests for SOC 2 audit initiation service (P3-B4)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base


# ---------------------------------------------------------------------------
# Fixture — in-memory SQLite with FK OFF (no groups table dependency)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    """Async SQLite session for SOC 2 unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Policy tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAuditPolicies:
    async def test_create_policy_returns_policy(self, db):
        """create_policy persists and returns an AuditPolicy."""
        from src.compliance.soc2 import create_policy

        policy = await create_policy(
            db,
            name="Access Control Policy",
            category="security",
            description="RBAC and API key management",
            version="1.0",
        )
        assert policy.id is not None
        assert policy.name == "Access Control Policy"
        assert policy.category == "security"
        assert policy.version == "1.0"

    async def test_create_policy_with_effective_date(self, db):
        """create_policy accepts and stores effective_date."""
        from src.compliance.soc2 import create_policy

        effective = datetime(2026, 3, 24, tzinfo=timezone.utc)
        policy = await create_policy(
            db,
            name="Encryption Policy",
            category="confidentiality",
            description="Data encryption standards",
            version="2.0",
            effective_date=effective,
        )
        assert policy.effective_date is not None

    async def test_get_policies_returns_all(self, db):
        """get_policies returns all policies when no category filter."""
        from src.compliance.soc2 import create_policy, get_policies

        await create_policy(db, name="Policy A", category="security", description=None)
        await create_policy(db, name="Policy B", category="availability", description=None)

        policies = await get_policies(db)
        assert len(policies) == 2

    async def test_get_policies_filtered_by_category(self, db):
        """get_policies respects category filter."""
        from src.compliance.soc2 import create_policy, get_policies

        await create_policy(db, name="Policy A", category="security", description=None)
        await create_policy(db, name="Policy B", category="privacy", description=None)
        await create_policy(db, name="Policy C", category="security", description=None)

        security_policies = await get_policies(db, category="security")
        assert len(security_policies) == 2
        assert all(p.category == "security" for p in security_policies)

    async def test_get_policies_empty_category_returns_none(self, db):
        """get_policies with unknown category returns empty list."""
        from src.compliance.soc2 import create_policy, get_policies

        await create_policy(db, name="Policy A", category="security", description=None)

        policies = await get_policies(db, category="confidentiality")
        assert policies == []


# ---------------------------------------------------------------------------
# Evidence collection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEvidenceCollection:
    async def test_collect_evidence_creates_three_records(self, db):
        """collect_evidence creates deployment_log, access_control, encryption records."""
        from src.compliance.soc2 import collect_evidence

        items = await collect_evidence(db)
        assert len(items) == 3

    async def test_collect_evidence_types(self, db):
        """collect_evidence creates records with the expected evidence types."""
        from src.compliance.soc2 import collect_evidence

        items = await collect_evidence(db)
        types = {item.evidence_type for item in items}
        assert "deployment_log" in types
        assert "access_control" in types
        assert "encryption" in types

    async def test_collect_evidence_has_data(self, db):
        """Each collected evidence record has a non-empty data dict."""
        from src.compliance.soc2 import collect_evidence

        items = await collect_evidence(db)
        for item in items:
            assert item.data is not None
            assert isinstance(item.data, dict)
            assert len(item.data) > 0

    async def test_collect_evidence_has_ids(self, db):
        """Collected evidence records have persisted UUIDs."""
        from src.compliance.soc2 import collect_evidence

        items = await collect_evidence(db)
        for item in items:
            assert item.id is not None

    async def test_collect_evidence_deployment_log_content(self, db):
        """deployment_log evidence contains expected keys."""
        from src.compliance.soc2 import collect_evidence

        items = await collect_evidence(db)
        deploy_log = next(i for i in items if i.evidence_type == "deployment_log")
        assert "app_version" in deploy_log.data
        assert "deployment_method" in deploy_log.data


# ---------------------------------------------------------------------------
# Readiness report tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReadinessReport:
    async def test_readiness_report_structure(self, db):
        """get_readiness_report returns the expected top-level keys."""
        from src.compliance.soc2 import get_readiness_report

        report = await get_readiness_report(db)
        assert "generated_at" in report
        assert "overall_readiness_pct" in report
        assert "total_controls" in report
        assert "categories" in report
        assert "controls" in report

    async def test_readiness_report_categories(self, db):
        """get_readiness_report includes all four TSC category keys."""
        from src.compliance.soc2 import get_readiness_report

        report = await get_readiness_report(db)
        categories = report["categories"]
        assert "security" in categories
        assert "availability" in categories
        assert "confidentiality" in categories
        assert "privacy" in categories

    async def test_readiness_report_empty_controls(self, db):
        """Readiness report with no controls reports 0 total and 0% readiness."""
        from src.compliance.soc2 import get_readiness_report

        report = await get_readiness_report(db)
        assert report["total_controls"] == 0
        assert report["overall_readiness_pct"] == 0.0

    async def test_readiness_report_with_controls(self, db):
        """Readiness percentage computed correctly from ComplianceControl records."""
        from src.compliance.soc2 import get_readiness_report, update_control_status

        await update_control_status(db, "CC6.1", "implemented")
        await update_control_status(db, "CC6.2", "implemented")
        await update_control_status(db, "CC7.1", "partial")

        report = await get_readiness_report(db)
        assert report["total_controls"] == 3
        assert report["implemented"] == 2
        assert report["overall_readiness_pct"] == pytest.approx(66.7, abs=0.1)


# ---------------------------------------------------------------------------
# Control status tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestControlStatus:
    async def test_update_control_creates_new(self, db):
        """update_control_status creates a new record when control_id is unknown."""
        from src.compliance.soc2 import update_control_status

        ctrl = await update_control_status(db, "CC6.1", "implemented")
        assert ctrl.control_id == "CC6.1"
        assert ctrl.status == "implemented"
        assert ctrl.id is not None

    async def test_update_control_updates_existing(self, db):
        """update_control_status updates an existing record (upsert)."""
        from src.compliance.soc2 import update_control_status

        await update_control_status(db, "CC6.2", "planned")
        ctrl = await update_control_status(db, "CC6.2", "implemented", description="Auth done")

        assert ctrl.control_id == "CC6.2"
        assert ctrl.status == "implemented"
        assert ctrl.description == "Auth done"

    async def test_update_control_stores_evidence_ids(self, db):
        """update_control_status stores evidence_ids list."""
        from src.compliance.soc2 import update_control_status

        eid = str(uuid4())
        ctrl = await update_control_status(db, "P1.1", "partial", evidence_ids=[eid])
        assert eid in ctrl.evidence_ids

    async def test_update_control_category_mapping(self, db):
        """_infer_category maps control IDs to the correct TSC category."""
        from src.compliance.soc2 import _infer_category

        assert _infer_category("CC6.1") == "security"
        assert _infer_category("A1.1") == "availability"
        assert _infer_category("C1.1") == "confidentiality"
        assert _infer_category("P1.1") == "privacy"
