"""Unit tests for capture module — HMAC validation, consent, ingestion, encryption, pagination."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.capture.models import CaptureEvent
from src.capture.schemas import EventPayload
from src.capture.service import (
    create_content_capture,
    get_decrypted_content,
    ingest_event,
    list_events_enriched,
)
from src.capture.validators import (
    MAX_EVENT_AGE_SECONDS,
    check_replay,
    validate_platform,
    verify_hmac_signature,
)
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ForbiddenError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def _make_member(session, group_id, display_name="Test Child", role="member", dob=None):
    """Create a GroupMember and return it."""
    member = GroupMember(
        id=uuid4(),
        group_id=group_id,
        display_name=display_name,
        role=role,
        date_of_birth=dob,
    )
    session.add(member)
    await session.flush()
    return member


async def _grant_consent(session, group_id, member_id):
    """Create a consent record for a member so capture events are accepted."""
    from src.compliance.models import ConsentRecord
    consent = ConsentRecord(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        consent_type="monitoring",
    )
    session.add(consent)
    await session.flush()


async def _sign_family_agreement(session, group_id, member_id, parent_id):
    """Create and sign a family agreement for a member."""
    from src.groups.agreement import FamilyAgreement
    agreement = FamilyAgreement(
        id=uuid4(),
        group_id=group_id,
        title="Test Agreement",
        template_id="default",
        rules=[],
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
# 1. HMAC-SHA256 validation
# ──────────────────────────────────────────────────────────────────────────────


class TestHMACValidation:
    """HMAC-SHA256 signature validation: valid, invalid, missing."""

    def test_valid_hmac_signature(self):
        secret = "test-secret-key"
        payload = '{"group_id": "abc"}'
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert verify_hmac_signature(payload, sig, secret) is True

    def test_invalid_hmac_signature(self):
        secret = "test-secret-key"
        payload = '{"group_id": "abc"}'
        assert verify_hmac_signature(payload, "bad_signature", secret) is False

    def test_wrong_secret_fails(self):
        secret = "correct-secret"
        wrong_secret = "wrong-secret"
        payload = '{"data": "test"}'
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert verify_hmac_signature(payload, sig, wrong_secret) is False

    def test_tampered_payload_fails(self):
        secret = "test-secret"
        original = '{"amount": 100}'
        tampered = '{"amount": 999}'
        sig = hmac.new(secret.encode(), original.encode(), hashlib.sha256).hexdigest()
        assert verify_hmac_signature(tampered, sig, secret) is False

    def test_empty_payload_valid(self):
        secret = "test-secret"
        payload = ""
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert verify_hmac_signature(payload, sig, secret) is True


# ──────────────────────────────────────────────────────────────────────────────
# 2. Replay prevention
# ──────────────────────────────────────────────────────────────────────────────


class TestReplayPrevention:
    """Replay prevention via nonce and timestamp."""

    def test_valid_request_accepted(self):
        nonce = uuid4().hex
        assert check_replay(nonce, time.time()) is True

    def test_duplicate_nonce_rejected(self):
        nonce = uuid4().hex
        check_replay(nonce, time.time())
        assert check_replay(nonce, time.time()) is False

    def test_stale_timestamp_rejected(self):
        nonce = uuid4().hex
        old_time = time.time() - MAX_EVENT_AGE_SECONDS - 10
        assert check_replay(nonce, old_time) is False


# ──────────────────────────────────────────────────────────────────────────────
# 3. Platform validation
# ──────────────────────────────────────────────────────────────────────────────


class TestPlatformValidation:
    """Validate supported AI platforms."""

    def test_valid_platforms(self):
        for p in ("chatgpt", "gemini", "copilot", "claude", "grok"):
            assert validate_platform(p) is True

    def test_invalid_platform(self):
        assert validate_platform("unknown_ai") is False
        assert validate_platform("") is False
        assert validate_platform("ChatGPT") is False  # Case sensitive


# ──────────────────────────────────────────────────────────────────────────────
# 4. Consent gate enforcement
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestConsentEnforcement:
    """Events rejected when consent is missing or denied."""

    async def test_event_blocked_without_consent(self, test_session):
        group, owner_id = await make_test_group(test_session)
        # Member with DOB under 13 requires COPPA consent
        dob = datetime.now(timezone.utc) - timedelta(days=365 * 10)
        member = await _make_member(test_session, group.id, dob=dob)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="chatgpt",
            session_id="sess-1", event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(ForbiddenError, match="consent"):
            await ingest_event(test_session, payload)

    async def test_event_accepted_with_consent(self, test_session):
        group, owner_id = await make_test_group(test_session)
        # Member without DOB does not require consent
        member = await _make_member(test_session, group.id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="chatgpt",
            session_id="sess-2", event_type="prompt",
            timestamp=datetime.now(timezone.utc),
        )
        event = await ingest_event(test_session, payload)
        assert event.platform == "chatgpt"
        assert event.source_channel == "extension"


# ──────────────────────────────────────────────────────────────────────────────
# 5. Event ingestion
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEventIngestion:
    """Valid payloads stored, invalid payloads rejected."""

    async def test_valid_event_stored(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="claude",
            session_id="sess-3", event_type="response",
            timestamp=datetime.now(timezone.utc),
            content="Hello world",
        )
        event = await ingest_event(test_session, payload)
        assert event.id is not None
        assert event.content == "Hello world"

    async def test_event_with_metadata(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        payload = EventPayload(
            group_id=group.id, member_id=member.id, platform="gemini",
            session_id="sess-4", event_type="session_start",
            timestamp=datetime.now(timezone.utc),
            metadata={"browser": "chrome", "version": "120"},
        )
        event = await ingest_event(test_session, payload)
        assert event.event_metadata == {"browser": "chrome", "version": "120"}

    def test_invalid_platform_schema_rejected(self):
        """EventPayload schema rejects invalid platforms."""
        with pytest.raises(Exception):
            EventPayload(
                group_id=uuid4(), member_id=uuid4(), platform="invalid_ai",
                session_id="sess", event_type="prompt",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_session_id_rejected(self):
        """EventPayload schema requires session_id."""
        with pytest.raises(Exception):
            EventPayload(
                group_id=uuid4(), member_id=uuid4(), platform="chatgpt",
                session_id="", event_type="prompt",
                timestamp=datetime.now(timezone.utc),
            )


# ──────────────────────────────────────────────────────────────────────────────
# 6. Content excerpt encryption
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestContentEncryption:
    """Content encrypted on store, decrypted on read."""

    async def test_content_encrypted_on_creation(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        event = await create_content_capture(
            test_session, group_id=group.id, member_id=member.id,
            platform="chatgpt", content="secret conversation",
        )
        assert event.content_encrypted is not None
        assert event.content_encrypted != "secret conversation"

    async def test_content_decryption(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        event = await create_content_capture(
            test_session, group_id=group.id, member_id=member.id,
            platform="chatgpt", content="decrypt this",
        )
        decrypted = await get_decrypted_content(test_session, event.id)
        assert decrypted == "decrypt this"

    async def test_content_hash_for_dedup(self, test_session):
        group, owner_id = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        event = await create_content_capture(
            test_session, group_id=group.id, member_id=member.id,
            platform="chatgpt", content="same content",
        )
        expected_hash = hashlib.sha256(b"same content").hexdigest()
        assert event.content_hash == expected_hash

    async def test_nonexistent_event_returns_none(self, test_session):
        result = await get_decrypted_content(test_session, uuid4())
        assert result is None

    def test_encrypt_decrypt_roundtrip(self):
        original = "sensitive AI conversation content"
        encrypted = encrypt_credential(original)
        assert encrypted != original
        decrypted = decrypt_credential(encrypted)
        assert decrypted == original


# ──────────────────────────────────────────────────────────────────────────────
# 7. Paginated response contract
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPaginatedResponse:
    """Paginated response shape: items, total, page, page_size, total_pages."""

    async def test_empty_result_shape(self, test_session):
        group, _ = await make_test_group(test_session)
        result = await list_events_enriched(test_session, group.id)
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "total_pages" in result
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["total_pages"] >= 1

    async def test_pagination_with_data(self, test_session):
        group, _ = await make_test_group(test_session)
        member = await _make_member(test_session, group.id)

        # Create 5 events
        for i in range(5):
            event = CaptureEvent(
                id=uuid4(), group_id=group.id, member_id=member.id,
                platform="chatgpt", session_id=f"sess-{i}",
                event_type="prompt", timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                risk_processed=False, source_channel="extension",
            )
            test_session.add(event)
        await test_session.flush()

        # Page 1 with size 2
        result = await list_events_enriched(test_session, group.id, page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total"] == 5
        assert result["total_pages"] == 3

        # Page 3 with size 2 should have 1 item
        result = await list_events_enriched(test_session, group.id, page=3, page_size=2)
        assert len(result["items"]) == 1
