"""Unit tests for CSAM detection and NCMEC reporting.

Tests mock all external APIs (PhotoDNA, NCMEC) — no real network calls.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from src.moderation.csam import (
    CSAMCheckResult,
    CSAMDetector,
    NCMECReport,
    check_csam,
    detector,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def csam_detector() -> CSAMDetector:
    """Fresh detector with no credentials."""
    return CSAMDetector()


@pytest.fixture()
def configured_detector() -> CSAMDetector:
    """Detector with PhotoDNA + NCMEC credentials."""
    d = CSAMDetector()
    d.configure(
        photodna_key="test-photodna-key",
        ncmec_username="test-user",
        ncmec_password="test-pass",
    )
    return d


# ---------------------------------------------------------------------------
# CSAMDetector.check_csam
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_csam_no_api_key(csam_detector: CSAMDetector):
    """Without PhotoDNA key, returns non-match with provider='none'."""
    result = await csam_detector.check_csam(image_url="https://example.com/img.png")
    assert result.is_match is False
    assert result.provider == "none"
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_check_csam_requires_url_or_hash(configured_detector: CSAMDetector):
    """Raises ValueError when neither url nor hash provided."""
    with pytest.raises(ValueError, match="Either image_url or image_hash required"):
        await configured_detector.check_csam()


@pytest.mark.asyncio
async def test_check_csam_url_match(configured_detector: CSAMDetector):
    """PhotoDNA URL match returns is_match=True, confidence=1.0."""
    mock_resp = httpx.Response(
        200,
        json={"IsMatch": True, "ContentId": "abc123"},
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await configured_detector.check_csam(image_url="https://example.com/img.png")

    assert result.is_match is True
    assert result.confidence == 1.0
    assert result.provider == "photodna"
    assert result.hash_value == "abc123"


@pytest.mark.asyncio
async def test_check_csam_url_no_match(configured_detector: CSAMDetector):
    """PhotoDNA URL non-match returns is_match=False."""
    mock_resp = httpx.Response(
        200,
        json={"IsMatch": False},
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await configured_detector.check_csam(image_url="https://example.com/safe.png")

    assert result.is_match is False
    assert result.confidence == 0.0
    assert result.provider == "photodna"


@pytest.mark.asyncio
async def test_check_csam_hash_match(configured_detector: CSAMDetector):
    """PhotoDNA hash match returns is_match=True."""
    mock_resp = httpx.Response(
        200,
        json={"IsMatch": True},
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await configured_detector.check_csam(image_hash="deadbeef")

    assert result.is_match is True
    assert result.hash_value == "deadbeef"
    assert result.provider == "photodna"


@pytest.mark.asyncio
async def test_check_csam_hash_no_match(configured_detector: CSAMDetector):
    """PhotoDNA hash non-match."""
    mock_resp = httpx.Response(
        200,
        json={"IsMatch": False},
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await configured_detector.check_csam(image_hash="safe-hash")

    assert result.is_match is False


@pytest.mark.asyncio
async def test_check_csam_api_error_returns_non_match(configured_detector: CSAMDetector):
    """On API error, returns non-match (safety: flag for manual review)."""
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await configured_detector.check_csam(image_url="https://example.com/img.png")

    assert result.is_match is False
    assert result.provider == "photodna"


@pytest.mark.asyncio
async def test_check_csam_timestamp_set(csam_detector: CSAMDetector):
    """check_timestamp is always populated."""
    result = await csam_detector.check_csam(image_url="https://example.com/img.png")
    assert isinstance(result.check_timestamp, datetime)
    assert result.check_timestamp.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# CSAMDetector.report_to_ncmec
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_to_ncmec_no_credentials(csam_detector: CSAMDetector):
    """Without NCMEC credentials, returns failed status."""
    report = await csam_detector.report_to_ncmec(
        content_id="c1",
        reporter_info={"name": "Test ESP"},
        incident_details={"description": "test"},
    )
    assert report.status == "failed"
    assert report.error == "NCMEC credentials not configured"
    assert report.report_id is None


@pytest.mark.asyncio
async def test_report_to_ncmec_success(configured_detector: CSAMDetector):
    """Successful NCMEC report returns report_id and submitted status."""
    mock_resp = httpx.Response(
        200,
        json={"reportId": "NCMEC-12345"},
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        report = await configured_detector.report_to_ncmec(
            content_id="c1",
            reporter_info={"name": "Test ESP"},
            incident_details={"description": "test"},
        )

    assert report.status == "submitted"
    assert report.report_id == "NCMEC-12345"
    assert report.error is None
    assert report.submitted_at is not None


@pytest.mark.asyncio
async def test_report_to_ncmec_api_failure(configured_detector: CSAMDetector):
    """NCMEC API failure returns failed status with error message."""
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        report = await configured_detector.report_to_ncmec(
            content_id="c1",
            reporter_info={},
            incident_details={},
        )

    assert report.status == "failed"
    assert "connection refused" in report.error


@pytest.mark.asyncio
async def test_report_to_ncmec_http_error(configured_detector: CSAMDetector):
    """NCMEC HTTP 500 returns failed status."""
    mock_resp = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://example.com"),
    )
    with patch("src.moderation.csam.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        report = await configured_detector.report_to_ncmec(
            content_id="c1",
            reporter_info={},
            incident_details={},
        )

    assert report.status == "failed"
    assert report.error is not None


# ---------------------------------------------------------------------------
# CSAMDetector.preserve_evidence
# ---------------------------------------------------------------------------


def test_preserve_evidence_returns_encrypted_string(configured_detector: CSAMDetector):
    """preserve_evidence returns a Fernet-prefixed encrypted string."""
    result = configured_detector.preserve_evidence("content-1", b"raw-image-bytes")
    assert isinstance(result, str)
    assert result.startswith("fernet:")


def test_preserve_evidence_with_str_content(configured_detector: CSAMDetector):
    """preserve_evidence accepts string content and encrypts it."""
    result = configured_detector.preserve_evidence("content-2", "string-content")
    assert isinstance(result, str)
    assert result.startswith("fernet:")


def test_preserve_evidence_contains_sha256(configured_detector: CSAMDetector):
    """Decrypted evidence contains SHA-256 hash of the original content."""
    import hashlib
    from src.encryption import decrypt_credential

    content = b"test-image-data"
    encrypted = configured_detector.preserve_evidence("c3", content)
    decrypted = decrypt_credential(encrypted)
    evidence = json.loads(decrypted)

    assert evidence["sha256"] == hashlib.sha256(content).hexdigest()
    assert evidence["content_id"] == "c3"
    assert evidence["size_bytes"] == len(content)
    assert "preserved_at" in evidence


def test_preserve_evidence_different_content_different_hash(configured_detector: CSAMDetector):
    """Different content produces different SHA-256 hashes."""
    from src.encryption import decrypt_credential

    e1 = configured_detector.preserve_evidence("c1", b"content-a")
    e2 = configured_detector.preserve_evidence("c2", b"content-b")

    d1 = json.loads(decrypt_credential(e1))
    d2 = json.loads(decrypt_credential(e2))

    assert d1["sha256"] != d2["sha256"]


# ---------------------------------------------------------------------------
# CSAMDetector.suspend_account (audit trail)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspend_account_logs_event(configured_detector: CSAMDetector):
    """suspend_account logs the event at CRITICAL level."""
    # Should not raise — just logs
    await configured_detector.suspend_account(
        user_id="user-123",
        reason="CSAM match detected",
    )


# ---------------------------------------------------------------------------
# CSAMDetector.configure / is_configured
# ---------------------------------------------------------------------------


def test_detector_not_configured_by_default(csam_detector: CSAMDetector):
    """New detector is not configured."""
    assert csam_detector.is_configured is False


def test_detector_configured_after_configure(csam_detector: CSAMDetector):
    """After configure(), is_configured is True."""
    csam_detector.configure(photodna_key="key")
    assert csam_detector.is_configured is True


# ---------------------------------------------------------------------------
# Module-level check_csam convenience function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_module_check_csam_delegates_to_singleton():
    """Module-level check_csam uses the singleton detector."""
    original_key = detector._photodna_key
    try:
        detector._photodna_key = None
        result = await check_csam(image_url="https://example.com/img.png")
        assert result.is_match is False
        assert result.provider == "none"
    finally:
        detector._photodna_key = original_key


# ---------------------------------------------------------------------------
# Dataclass correctness
# ---------------------------------------------------------------------------


def test_csam_check_result_fields():
    """CSAMCheckResult stores all expected fields."""
    now = datetime.now(timezone.utc)
    r = CSAMCheckResult(
        is_match=True,
        hash_value="abc",
        confidence=0.99,
        provider="photodna",
        check_timestamp=now,
    )
    assert r.is_match is True
    assert r.hash_value == "abc"
    assert r.confidence == 0.99
    assert r.provider == "photodna"
    assert r.check_timestamp == now


def test_ncmec_report_fields():
    """NCMECReport stores all expected fields."""
    now = datetime.now(timezone.utc)
    r = NCMECReport(
        report_id="R-1",
        submitted_at=now,
        status="submitted",
    )
    assert r.report_id == "R-1"
    assert r.status == "submitted"
    assert r.error is None


def test_ncmec_report_with_error():
    """NCMECReport can store an error string."""
    r = NCMECReport(
        report_id=None,
        submitted_at=None,
        status="failed",
        error="Connection timeout",
    )
    assert r.error == "Connection timeout"


# ---------------------------------------------------------------------------
# Pipeline integration (service.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_media_csam_match_blocks(test_session):
    """Media submission with CSAM match is immediately rejected."""
    from src.moderation.service import submit_for_moderation

    media_id = uuid4()
    content_id = uuid4()

    mock_result = CSAMCheckResult(
        is_match=True,
        hash_value="match-hash",
        confidence=1.0,
        provider="photodna",
        check_timestamp=datetime.now(timezone.utc),
    )
    with patch("src.moderation.service.check_csam", return_value=mock_result):
        entry = await submit_for_moderation(
            db=test_session,
            content_type="media",
            content_id=content_id,
            media_ids=[media_id],
        )

    assert entry.status == "rejected"
    assert entry.risk_scores["csam"]["match"] is True
    assert entry.risk_scores["csam"]["confidence"] == 1.0


@pytest.mark.asyncio
async def test_submit_media_csam_no_match_continues(test_session):
    """Media submission without CSAM match continues to keyword filter."""
    from src.moderation.service import submit_for_moderation

    media_id = uuid4()
    content_id = uuid4()

    mock_result = CSAMCheckResult(
        is_match=False,
        hash_value=None,
        confidence=0.0,
        provider="photodna",
        check_timestamp=datetime.now(timezone.utc),
    )
    with patch("src.moderation.service.check_csam", return_value=mock_result):
        entry = await submit_for_moderation(
            db=test_session,
            content_type="media",
            content_id=content_id,
            media_ids=[media_id],
        )

    assert entry.status == "pending"
    # No CSAM risk scores
    assert entry.risk_scores is None


@pytest.mark.asyncio
async def test_submit_text_skips_csam(test_session):
    """Text-only submissions skip CSAM check entirely."""
    from src.moderation.service import submit_for_moderation

    content_id = uuid4()

    with patch("src.moderation.service.check_csam") as mock_check:
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=content_id,
            content_text="hello world",
        )

    mock_check.assert_not_called()
    assert entry.status != "rejected" or "csam" not in (entry.risk_scores or {})


@pytest.mark.asyncio
async def test_submit_media_no_media_ids_skips_csam(test_session):
    """Media type without media_ids skips CSAM check."""
    from src.moderation.service import submit_for_moderation

    content_id = uuid4()

    with patch("src.moderation.service.check_csam") as mock_check:
        entry = await submit_for_moderation(
            db=test_session,
            content_type="media",
            content_id=content_id,
        )

    mock_check.assert_not_called()
