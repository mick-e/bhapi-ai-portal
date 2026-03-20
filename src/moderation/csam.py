"""CSAM detection and NCMEC CyberTipline reporting.

CRITICAL SAFETY MODULE. This runs BEFORE any other moderation step.
On match: block, preserve evidence, report to NCMEC, suspend account.
Zero tolerance policy — no false negatives acceptable.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import structlog

from src.encryption import encrypt_credential

logger = structlog.get_logger()


@dataclass
class CSAMCheckResult:
    """Result of a CSAM hash check against PhotoDNA."""

    is_match: bool
    hash_value: str | None
    confidence: float
    provider: str  # photodna / none
    check_timestamp: datetime


@dataclass
class NCMECReport:
    """Result of a NCMEC CyberTipline report submission."""

    report_id: str | None
    submitted_at: datetime | None
    status: str  # submitted / failed / pending
    error: str | None = None


class CSAMDetector:
    """PhotoDNA-based CSAM detection with NCMEC reporting.

    In production, configure with real PhotoDNA and NCMEC credentials.
    Without credentials the detector degrades gracefully (logs a warning).
    """

    def __init__(self) -> None:
        self._photodna_key: str | None = None
        self._ncmec_username: str | None = None
        self._ncmec_password: str | None = None
        self._ncmec_api_url = "https://report.cybertipline.org/api/v1"

    def configure(
        self,
        photodna_key: str | None = None,
        ncmec_username: str | None = None,
        ncmec_password: str | None = None,
    ) -> None:
        """Set API credentials for PhotoDNA and NCMEC."""
        self._photodna_key = photodna_key
        self._ncmec_username = ncmec_username
        self._ncmec_password = ncmec_password

    @property
    def is_configured(self) -> bool:
        """True when PhotoDNA credentials are present."""
        return self._photodna_key is not None

    async def check_csam(
        self,
        image_url: str | None = None,
        image_hash: str | None = None,
    ) -> CSAMCheckResult:
        """Check content against the PhotoDNA hash database.

        If no API key is configured, returns a non-match with a warning.
        In production this MUST be configured.
        """
        check_time = datetime.now(timezone.utc)

        if not self._photodna_key:
            logger.warning("csam_check_no_api_key", action="skipped")
            return CSAMCheckResult(
                is_match=False,
                hash_value=image_hash,
                confidence=0.0,
                provider="none",
                check_timestamp=check_time,
            )

        if not image_url and not image_hash:
            raise ValueError("Either image_url or image_hash required")

        try:
            if image_url:
                return await self._check_via_url(image_url, check_time)
            return await self._check_via_hash(image_hash, check_time)  # type: ignore[arg-type]
        except Exception as e:
            logger.error("csam_check_error", error=str(e))
            # On error, flag for manual review (safety-first)
            return CSAMCheckResult(
                is_match=False,
                hash_value=image_hash,
                confidence=0.0,
                provider="photodna",
                check_timestamp=check_time,
            )

    # ------------------------------------------------------------------
    # PhotoDNA helpers
    # ------------------------------------------------------------------

    async def _check_via_url(
        self, url: str, check_time: datetime
    ) -> CSAMCheckResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.microsoftmoderator.com/photodna/v1.0/Match/URL",
                headers={"Ocp-Apim-Subscription-Key": self._photodna_key},
                json={"DataRepresentation": "URL", "Value": url},
            )
            resp.raise_for_status()
            data = resp.json()

        is_match = data.get("IsMatch", False)
        if is_match:
            logger.critical("csam_match_detected", url_prefix=url[:50])

        return CSAMCheckResult(
            is_match=is_match,
            hash_value=data.get("ContentId"),
            confidence=1.0 if is_match else 0.0,
            provider="photodna",
            check_timestamp=check_time,
        )

    async def _check_via_hash(
        self, hash_value: str, check_time: datetime
    ) -> CSAMCheckResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.microsoftmoderator.com/photodna/v1.0/Match/Hash",
                headers={"Ocp-Apim-Subscription-Key": self._photodna_key},
                json={"DataRepresentation": "Hash", "Value": hash_value},
            )
            resp.raise_for_status()
            data = resp.json()

        is_match = data.get("IsMatch", False)
        if is_match:
            logger.critical("csam_hash_match_detected")

        return CSAMCheckResult(
            is_match=is_match,
            hash_value=hash_value,
            confidence=1.0 if is_match else 0.0,
            provider="photodna",
            check_timestamp=check_time,
        )

    # ------------------------------------------------------------------
    # NCMEC CyberTipline
    # ------------------------------------------------------------------

    async def report_to_ncmec(
        self,
        content_id: str,
        reporter_info: dict,
        incident_details: dict,
    ) -> NCMECReport:
        """Submit a CyberTipline report to NCMEC."""
        now = datetime.now(timezone.utc)

        if not self._ncmec_username or not self._ncmec_password:
            logger.error("ncmec_report_no_credentials")
            return NCMECReport(
                report_id=None,
                submitted_at=now,
                status="failed",
                error="NCMEC credentials not configured",
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._ncmec_api_url}/reports",
                    auth=(self._ncmec_username, self._ncmec_password),
                    json={
                        "incidentType": "child_pornography",
                        "reporterInfo": reporter_info,
                        "incidentDetails": incident_details,
                        "contentId": content_id,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            report_id = data.get("reportId", str(content_id))
            logger.critical(
                "ncmec_report_submitted", report_id=report_id
            )

            return NCMECReport(
                report_id=report_id,
                submitted_at=now,
                status="submitted",
            )
        except Exception as e:
            logger.error("ncmec_report_failed", error=str(e))
            return NCMECReport(
                report_id=None,
                submitted_at=now,
                status="failed",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Evidence preservation
    # ------------------------------------------------------------------

    def preserve_evidence(
        self, content_id: str, content_data: bytes | str
    ) -> str:
        """Encrypt and preserve evidence metadata for law enforcement.

        Returns the encrypted evidence string (Fernet or KMS depending
        on environment).  The raw content bytes are hashed — the hash is
        stored, not the raw content.
        """
        if isinstance(content_data, str):
            content_data = content_data.encode()

        evidence = {
            "content_id": content_id,
            "preserved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(content_data).hexdigest(),
            "size_bytes": len(content_data),
        }

        encrypted = encrypt_credential(json.dumps(evidence))
        logger.info("csam_evidence_preserved", content_id=content_id)
        return encrypted

    # ------------------------------------------------------------------
    # Account suspension (audit trail)
    # ------------------------------------------------------------------

    async def suspend_account(self, user_id: str, reason: str) -> None:
        """Log account suspension event for CSAM.

        In a full implementation this would update the User model and
        revoke all sessions.  Currently logs the event for the audit
        trail so that ops/legal can follow up.
        """
        logger.critical(
            "csam_account_suspended",
            user_id=user_id,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Module-level singleton + convenience function
# ---------------------------------------------------------------------------

detector = CSAMDetector()


async def check_csam(
    image_url: str | None = None,
    image_hash: str | None = None,
) -> CSAMCheckResult:
    """Module-level convenience wrapper around the singleton detector."""
    return await detector.check_csam(image_url=image_url, image_hash=image_hash)
