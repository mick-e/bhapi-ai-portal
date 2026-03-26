"""Unit tests for Australian Online Safety compliance module.

Tests age verification enforcement, eSafety 24h SLA monitoring,
and cyberbullying case workflow.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.compliance.australian import (
    CYBERBULLYING_SEVERITIES,
    CYBERBULLYING_WORKFLOW_STEPS,
    ESAFETY_SLA_HOURS,
    VALID_VERIFICATION_METHODS,
    action_esafety_report,
    advance_cyberbullying_workflow,
    check_au_age_requirement,
    check_esafety_sla,
    close_cyberbullying_case,
    create_age_verification,
    create_cyberbullying_case,
    create_esafety_report,
    get_cyberbullying_case,
    get_esafety_report,
    list_cyberbullying_cases,
)
from src.compliance.australian_models import (
    ESafetyReport,
)
from src.database import Base

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_session():
    """In-memory SQLite session for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Age Verification Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_australian_age_verification_enforcement(test_session):
    """AU users must verify age before social access."""
    user_id = uuid4()

    # Before verification — AU user not verified
    result = await check_au_age_requirement(test_session, user_id, "AU")
    assert result["required"] is True
    assert result["verified"] is False
    assert result["verification"] is None

    # Create verification
    record = await create_age_verification(
        test_session, user_id, "AU", "yoti", {"session_id": "abc123"}
    )
    await test_session.commit()

    assert record.verified is True
    assert record.method == "yoti"
    assert record.country_code == "AU"
    assert record.verified_at is not None

    # After verification — AU user verified
    result = await check_au_age_requirement(test_session, user_id, "AU")
    assert result["required"] is True
    assert result["verified"] is True
    assert result["verification"]["method"] == "yoti"


@pytest.mark.asyncio
async def test_non_au_user_not_required(test_session):
    """Non-AU users do not need age verification."""
    user_id = uuid4()
    result = await check_au_age_requirement(test_session, user_id, "US")
    assert result["required"] is False
    assert result["verified"] is True


@pytest.mark.asyncio
async def test_age_verification_case_insensitive_country(test_session):
    """Country code is case-insensitive."""
    user_id = uuid4()
    result = await check_au_age_requirement(test_session, user_id, "au")
    assert result["required"] is True


@pytest.mark.asyncio
async def test_age_verification_invalid_method(test_session):
    """Invalid verification method raises ValidationError."""
    from src.exceptions import ValidationError

    with pytest.raises(ValidationError, match="Invalid verification method"):
        await create_age_verification(test_session, uuid4(), "AU", "invalid_method")


@pytest.mark.asyncio
async def test_age_verification_encrypts_data(test_session):
    """Verification data is encrypted at rest."""
    user_id = uuid4()
    record = await create_age_verification(
        test_session, user_id, "AU", "document",
        {"doc_type": "passport", "doc_number": "X123456"},
    )
    await test_session.commit()

    # The stored data should be encrypted (not plaintext JSON)
    assert record.verification_data is not None
    assert "passport" not in record.verification_data  # Encrypted, not plaintext


@pytest.mark.asyncio
async def test_age_verification_all_valid_methods(test_session):
    """All valid verification methods are accepted."""
    for method in VALID_VERIFICATION_METHODS:
        user_id = uuid4()
        record = await create_age_verification(test_session, user_id, "AU", method)
        await test_session.commit()
        assert record.method == method


@pytest.mark.asyncio
async def test_age_verification_multiple_records(test_session):
    """Latest verification is returned."""
    user_id = uuid4()
    await create_age_verification(test_session, user_id, "AU", "self_declaration")
    await test_session.commit()
    await create_age_verification(test_session, user_id, "AU", "yoti")
    await test_session.commit()

    result = await check_au_age_requirement(test_session, user_id, "AU")
    assert result["verified"] is True


# ---------------------------------------------------------------------------
# eSafety SLA Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_esafety_24h_sla_monitoring(test_session):
    """eSafety complaints actioned within 24 hours."""
    content_id = uuid4()
    report = await create_esafety_report(test_session, content_id, "post")
    await test_session.commit()

    assert report.status == "pending"
    assert report.sla_hours == 24

    # Action the report
    actioned = await action_esafety_report(test_session, report.id)
    await test_session.commit()

    assert actioned.status == "actioned"
    assert actioned.actioned_at is not None


@pytest.mark.asyncio
async def test_esafety_sla_compliant(test_session):
    """SLA is compliant when all reports actioned within 24h."""
    report = await create_esafety_report(test_session, uuid4(), "post")
    await test_session.commit()
    await action_esafety_report(test_session, report.id)
    await test_session.commit()

    sla = await check_esafety_sla(test_session)
    assert sla["compliant"] is True
    assert sla["breached"] == 0
    assert sla["compliance_rate"] == 100.0


@pytest.mark.asyncio
async def test_esafety_sla_breach_detection(test_session):
    """SLA breach detected when report actioned after 24 hours."""
    now = datetime.now(timezone.utc)
    report = ESafetyReport(
        id=uuid4(),
        content_id=uuid4(),
        content_type="post",
        reported_at=now - timedelta(hours=30),
        actioned_at=now,
        sla_hours=24,
        status="actioned",
    )
    test_session.add(report)
    await test_session.commit()

    sla = await check_esafety_sla(test_session)
    assert sla["breached"] == 1
    assert sla["compliant"] is False


@pytest.mark.asyncio
async def test_esafety_sla_pending_breach(test_session):
    """Pending reports exceeding SLA are counted as breached."""
    now = datetime.now(timezone.utc)
    report = ESafetyReport(
        id=uuid4(),
        content_id=uuid4(),
        content_type="comment",
        reported_at=now - timedelta(hours=25),
        sla_hours=24,
        status="pending",
    )
    test_session.add(report)
    await test_session.commit()

    sla = await check_esafety_sla(test_session)
    assert sla["pending"] == 1
    assert sla["breached"] == 1
    assert sla["compliant"] is False


@pytest.mark.asyncio
async def test_esafety_sla_no_reports(test_session):
    """Empty state — no reports means 100% compliant."""
    sla = await check_esafety_sla(test_session)
    assert sla["total_reports"] == 0
    assert sla["compliant"] is True
    assert sla["compliance_rate"] == 100.0


@pytest.mark.asyncio
async def test_esafety_report_generation(test_session):
    """eSafety Commissioner report includes SLA data and recent reports."""
    await create_esafety_report(test_session, uuid4(), "media")
    await test_session.commit()

    result = await get_esafety_report(test_session)
    assert result["report_type"] == "esafety_commissioner"
    assert "sla_compliance" in result
    assert len(result["recent_reports"]) == 1
    assert result["recent_reports"][0]["content_type"] == "media"


@pytest.mark.asyncio
async def test_esafety_report_not_found(test_session):
    """Actioning a non-existent report raises NotFoundError."""
    from src.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await action_esafety_report(test_session, uuid4())


# ---------------------------------------------------------------------------
# Cyberbullying Workflow Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cyberbullying_workflow(test_session):
    """Cyberbullying reports follow structured workflow."""
    reporter_id = uuid4()
    target_id = uuid4()

    case = await create_cyberbullying_case(
        test_session,
        reporter_id=reporter_id,
        target_id=target_id,
        evidence_ids=["ev1", "ev2"],
        severity="high",
        description="Repeated harassing messages",
    )
    await test_session.commit()

    assert case.status == "open"
    assert case.severity == "high"
    assert case.evidence_ids == ["ev1", "ev2"]
    assert len(case.workflow_steps) == len(CYBERBULLYING_WORKFLOW_STEPS)

    # First step (detect) should be auto-completed
    detect_step = case.workflow_steps[0]
    assert detect_step["step"] == "detect"
    assert detect_step["completed"] is True

    # Advance through workflow
    for step_name in ["document", "notify_parent", "review", "action"]:
        case = await advance_cyberbullying_workflow(
            test_session, case.id, step_name
        )
        await test_session.commit()

    # Verify steps are completed
    completed_steps = [s for s in case.workflow_steps if s["completed"]]
    assert len(completed_steps) == 5  # detect + 4 advanced


@pytest.mark.asyncio
async def test_cyberbullying_case_close(test_session):
    """Cyberbullying case can be closed with resolution."""
    case = await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), ["ev1"], "medium",
    )
    await test_session.commit()

    closed = await close_cyberbullying_case(
        test_session, case.id, "Warning issued to bully",
    )
    await test_session.commit()

    assert closed.status == "closed"
    assert closed.resolution == "Warning issued to bully"
    assert closed.resolved_at is not None


@pytest.mark.asyncio
async def test_cyberbullying_double_close(test_session):
    """Closing an already-closed case raises ValidationError."""
    from src.exceptions import ValidationError

    case = await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), [], "low",
    )
    await test_session.commit()

    await close_cyberbullying_case(test_session, case.id, "Resolved")
    await test_session.commit()

    with pytest.raises(ValidationError, match="already closed"):
        await close_cyberbullying_case(test_session, case.id, "Resolved again")


@pytest.mark.asyncio
async def test_cyberbullying_invalid_severity(test_session):
    """Invalid severity raises ValidationError."""
    from src.exceptions import ValidationError

    with pytest.raises(ValidationError, match="Invalid severity"):
        await create_cyberbullying_case(
            test_session, uuid4(), uuid4(), [], "extreme",
        )


@pytest.mark.asyncio
async def test_cyberbullying_case_not_found(test_session):
    """Getting a non-existent case raises NotFoundError."""
    from src.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await get_cyberbullying_case(test_session, uuid4())


@pytest.mark.asyncio
async def test_cyberbullying_invalid_workflow_step(test_session):
    """Advancing to unknown step raises ValidationError."""
    from src.exceptions import ValidationError

    case = await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), [], "low",
    )
    await test_session.commit()

    with pytest.raises(ValidationError, match="Unknown workflow step"):
        await advance_cyberbullying_workflow(test_session, case.id, "nonexistent")


@pytest.mark.asyncio
async def test_cyberbullying_list_cases(test_session):
    """List cyberbullying cases with optional filters."""
    await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), [], "low",
    )
    await test_session.commit()
    case2 = await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), [], "high",
    )
    await test_session.commit()
    await close_cyberbullying_case(test_session, case2.id, "Resolved")
    await test_session.commit()

    all_cases = await list_cyberbullying_cases(test_session)
    assert len(all_cases) == 2

    open_cases = await list_cyberbullying_cases(test_session, status="open")
    assert len(open_cases) == 1

    closed_cases = await list_cyberbullying_cases(test_session, status="closed")
    assert len(closed_cases) == 1


@pytest.mark.asyncio
async def test_cyberbullying_workflow_notes(test_session):
    """Workflow step advancement can include notes."""
    case = await create_cyberbullying_case(
        test_session, uuid4(), uuid4(), [], "medium",
    )
    await test_session.commit()

    case = await advance_cyberbullying_workflow(
        test_session, case.id, "document", notes="Screenshots collected",
    )
    await test_session.commit()

    doc_step = [s for s in case.workflow_steps if s["step"] == "document"][0]
    assert doc_step["completed"] is True
    assert doc_step["notes"] == "Screenshots collected"


@pytest.mark.asyncio
async def test_esafety_sla_constant(test_session):
    """SLA constant is 24 hours."""
    assert ESAFETY_SLA_HOURS == 24


@pytest.mark.asyncio
async def test_cyberbullying_all_severities(test_session):
    """All valid severities are accepted."""
    for sev in CYBERBULLYING_SEVERITIES:
        case = await create_cyberbullying_case(
            test_session, uuid4(), uuid4(), [], sev,
        )
        await test_session.commit()
        assert case.severity == sev
