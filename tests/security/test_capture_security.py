"""Security tests for capture module — HMAC bypass, consent enforcement, input validation."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.capture.models import CaptureEvent
from src.capture.schemas import EventPayload
from src.capture.service import create_content_capture, ingest_event, list_events_enriched
from src.capture.validators import (
    check_replay,
    validate_platform,
    verify_hmac_signature,
)
from src.database import Base, get_db
from src.exceptions import ForbiddenError, NotFoundError
from src.groups.models import GroupMember
from src.main import create_app
from tests.conftest import make_test_group


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def _make_member(session, group_id, display_name="Child", role="member", dob=None):
    member = GroupMember(
        id=uuid4(), group_id=group_id, display_name=display_name,
        role=role, date_of_birth=dob,
    )
    session.add(member)
    await session.flush()
    return member


async def _grant_consent(session, group_id, member_id):
    from src.compliance.models import ConsentRecord
    consent = ConsentRecord(
        id=uuid4(), group_id=group_id, member_id=member_id,
        consent_type="monitoring",
    )
    session.add(consent)
    await session.flush()


async def _sign_family_agreement(session, group_id, member_id, parent_id):
    from src.groups.agreement import FamilyAgreement
    agreement = FamilyAgreement(
        id=uuid4(), group_id=group_id, title="Agreement",
        template_id="default", rules=[],
        signed_by_parent=parent_id,
        signed_by_parent_at=datetime.now(timezone.utc),
        signed_by_members=[{"member_id": str(member_id), "name": "Child", "signed_at": datetime.now(timezone.utc).isoformat()}],
        active=True,
        review_due=datetime.now(timezone.utc).date() + timedelta(days=90),
    )
    session.add(agreement)
    await session.flush()
    return agreement


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: security test client
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def capture_sec_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────────
# 1. HMAC bypass attempts
# ──────────────────────────────────────────────────────────────────────────────


class TestHMACBypassAttempts:
    """Attempts to bypass HMAC validation must fail."""

    def test_empty_signature_rejected(self):
        assert verify_hmac_signature('{"data": "test"}', "", "secret") is False

    def test_wrong_algorithm_data_rejected(self):
        """Signature from a different algorithm should not match."""
        import hashlib
        secret = "test-secret"
        payload = '{"data": "test"}'
        # Use MD5 instead of SHA256
        wrong_sig = hmac.new(secret.encode(), payload.encode(), hashlib.md5).hexdigest()
        assert verify_hmac_signature(payload, wrong_sig, secret) is False

    def test_replay_attack_with_old_timestamp(self):
        """Stale timestamps are rejected to prevent replay attacks."""
        nonce = uuid4().hex
        stale_time = time.time() - 600  # 10 minutes old
        assert check_replay(nonce, stale_time) is False

    def test_replay_attack_with_reused_nonce(self):
        """Same nonce cannot be used twice."""
        nonce = f"replay-{uuid4().hex}"
        assert check_replay(nonce, time.time()) is True
        assert check_replay(nonce, time.time()) is False

    def test_future_timestamp_within_window(self):
        """Timestamps slightly in the future should be accepted (clock skew)."""
        nonce = uuid4().hex
        slight_future = time.time() + 30  # 30 seconds ahead
        assert check_replay(nonce, slight_future) is True

    def test_far_future_timestamp_rejected(self):
        """Timestamps far in the future should be rejected."""
        nonce = uuid4().hex
        far_future = time.time() + 600
        assert check_replay(nonce, far_future) is False


# ──────────────────────────────────────────────────────────────────────────────
# 2. Consent enforcement for children <13
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestChildConsentEnforcement:
    """Children under 13 require FamilyAgreement for capture."""

    async def test_child_under_13_blocked_without_agreement(self, test_session):
        group, owner_id = await make_test_group(test_session)
        # Child is 10 years old
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 10)
        member = await _make_member(test_session, group.id, dob=dob)
        await _grant_consent(test_session, group.id, member.id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="chatgpt",
            session_id="sess-child-1", event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(ForbiddenError, match="family agreement"):
            await ingest_event(test_session, payload)

    async def test_child_under_13_allowed_with_agreement(self, test_session):
        group, owner_id = await make_test_group(test_session)
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 10)
        member = await _make_member(test_session, group.id, dob=dob)
        await _grant_consent(test_session, group.id, member.id)
        await _sign_family_agreement(test_session, group.id, member.id, owner_id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="chatgpt",
            session_id="sess-child-2", event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None

    async def test_teen_allowed_without_agreement(self, test_session):
        """Members 13+ should not require family agreement."""
        group, owner_id = await make_test_group(test_session)
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 14)
        member = await _make_member(test_session, group.id, dob=dob)
        await _grant_consent(test_session, group.id, member.id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="gemini",
            session_id="sess-teen-1", event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None


# ──────────────────────────────────────────────────────────────────────────────
# 3. Content encryption security
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestContentEncryptionSecurity:
    """Content is encrypted at rest; raw content not stored in DB."""

    async def test_raw_content_not_in_db(self, test_session):
        group, _ = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        event = await create_content_capture(
            test_session, group_id=group.id, member_id=member.id,
            platform="chatgpt", content="PII: John Smith SSN 123-45-6789",
        )
        # Content_encrypted should not contain plaintext
        assert "John Smith" not in (event.content_encrypted or "")
        assert "123-45-6789" not in (event.content_encrypted or "")

    async def test_content_hash_is_one_way(self, test_session):
        """Content hash should not be reversible to original content."""
        group, _ = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        event = await create_content_capture(
            test_session, group_id=group.id, member_id=member.id,
            platform="chatgpt", content="secret data",
        )
        # Hash should be SHA-256 hex digest
        assert len(event.content_hash) == 64
        assert event.content_hash == hashlib.sha256(b"secret data").hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# 4. Input validation — oversized payloads, malicious content
# ──────────────────────────────────────────────────────────────────────────────


class TestInputValidation:
    """Input validation prevents oversized and malicious payloads."""

    def test_session_id_max_length(self):
        """session_id exceeding 255 chars should be rejected by schema."""
        with pytest.raises(Exception):
            EventPayload(
                group_id=uuid4(), member_id=uuid4(), platform="chatgpt",
                session_id="x" * 256, event_type="prompt",
                timestamp=datetime.now(timezone.utc),
            )

    def test_invalid_event_type_rejected(self):
        """event_type must be one of the allowed values."""
        with pytest.raises(Exception):
            EventPayload(
                group_id=uuid4(), member_id=uuid4(), platform="chatgpt",
                session_id="sess", event_type="malicious_type",
                timestamp=datetime.now(timezone.utc),
            )

    def test_sql_injection_in_platform_rejected(self):
        """SQL injection in platform field should be rejected by schema regex."""
        with pytest.raises(Exception):
            EventPayload(
                group_id=uuid4(), member_id=uuid4(),
                platform="chatgpt'; DROP TABLE capture_events;--",
                session_id="sess", event_type="prompt",
                timestamp=datetime.now(timezone.utc),
            )

    def test_xss_in_session_id_stored_safely(self):
        """XSS in session_id is stored as plain text (no execution context)."""
        # This should not raise — the schema allows it if within length
        payload = EventPayload(
            group_id=uuid4(), member_id=uuid4(), platform="chatgpt",
            session_id='<script>alert("xss")</script>',
            event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        # Verify it is stored as-is (no sanitization needed for DB storage)
        assert "<script>" in payload.session_id


# ──────────────────────────────────────────────────────────────────────────────
# 5. Cross-group capture isolation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCaptureIsolation:
    """Events from one group are not visible to another group."""

    async def test_events_isolated_between_groups(self, test_session):
        group_a, _ = await make_test_group(test_session, name="Group A")
        group_b, _ = await make_test_group(test_session, name="Group B")
        member_a = await _make_member(test_session, group_a.id, display_name="Child A")
        member_b = await _make_member(test_session, group_b.id, display_name="Child B")

        # Create events for group A
        for i in range(3):
            event = CaptureEvent(
                id=uuid4(), group_id=group_a.id, member_id=member_a.id,
                platform="chatgpt", session_id=f"sess-a-{i}",
                event_type="prompt", timestamp=datetime.now(timezone.utc),
                risk_processed=False, source_channel="extension",
            )
            test_session.add(event)

        # Create events for group B
        for i in range(2):
            event = CaptureEvent(
                id=uuid4(), group_id=group_b.id, member_id=member_b.id,
                platform="gemini", session_id=f"sess-b-{i}",
                event_type="prompt", timestamp=datetime.now(timezone.utc),
                risk_processed=False, source_channel="extension",
            )
            test_session.add(event)
        await test_session.flush()

        result_a = await list_events_enriched(test_session, group_a.id)
        result_b = await list_events_enriched(test_session, group_b.id)

        assert result_a["total"] == 3
        assert result_b["total"] == 2
        # Ensure no cross-contamination
        for item in result_a["items"]:
            assert item.group_id == group_a.id
        for item in result_b["items"]:
            assert item.group_id == group_b.id


# ──────────────────────────────────────────────────────────────────────────────
# 6. Capture endpoints require auth
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_capture_events_endpoint_requires_auth(capture_sec_client):
    """POST to /events without auth should fail."""
    resp = await capture_sec_client.post("/api/v1/capture/events", json={
        "group_id": str(uuid4()),
        "member_id": str(uuid4()),
        "platform": "chatgpt",
        "session_id": "sess-1",
        "event_type": "prompt",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_capture_list_endpoint_requires_auth(capture_sec_client):
    """GET /events without auth should fail."""
    resp = await capture_sec_client.get("/api/v1/capture/events")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_capture_content_endpoint_requires_auth(capture_sec_client):
    """POST to /content without auth should fail."""
    resp = await capture_sec_client.post("/api/v1/capture/content", json={
        "group_id": str(uuid4()),
        "member_id": str(uuid4()),
        "platform": "chatgpt",
        "content": "test content",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_pair_endpoint_is_public(capture_sec_client):
    """POST to /pair should be accessible without auth (it validates the code)."""
    resp = await capture_sec_client.post("/api/v1/capture/pair", json={
        "setup_code": "invalid_code",
    })
    # Should get 404 (code not found) rather than 401 (no auth)
    assert resp.status_code in (404, 422, 500)
    assert resp.status_code != 401
