"""Australian eSafety Commissioner compliance.

Handles complaint submission to eSafety Commissioner and 24h takedown SLA tracking.
Reference: docs/compliance/australian-online-safety-analysis.md
"""

import structlog
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

logger = structlog.get_logger()

TAKEDOWN_SLA_HOURS = 24


class ESafetyCategory(StrEnum):
    CYBERBULLYING = "cyberbullying"
    IMAGE_ABUSE = "image_based_abuse"
    ILLEGAL_CONTENT = "illegal_harmful_content"
    ONLINE_CONTENT = "online_content"


@dataclass
class ESafetyComplaint:
    complaint_id: str | None
    category: ESafetyCategory
    content_id: str
    submitted_at: datetime
    status: str  # pending/submitted/acknowledged/resolved/failed
    takedown_deadline: datetime
    error: str | None = None


@dataclass
class TakedownStatus:
    content_id: str
    deadline: datetime
    is_overdue: bool
    time_remaining_seconds: float
    taken_down: bool
    taken_down_at: datetime | None = None


class ESafetyPipeline:
    """eSafety Commissioner compliance pipeline."""

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._api_url = "https://api.esafety.gov.au/v1"
        self._pending_takedowns: dict[str, dict] = {}  # content_id -> metadata

    def configure(self, api_key: str | None = None, api_url: str | None = None) -> None:
        """Configure the pipeline with credentials."""
        self._api_key = api_key
        if api_url:
            self._api_url = api_url

    def reset(self) -> None:
        """Clear all state (for testing)."""
        self._api_key = None
        self._api_url = "https://api.esafety.gov.au/v1"
        self._pending_takedowns.clear()

    async def submit_complaint(
        self,
        content_id: str,
        category: ESafetyCategory,
        evidence_description: str,
        reporter_info: dict | None = None,
    ) -> ESafetyComplaint:
        """Submit a complaint to the eSafety Commissioner.

        Starts the 24h SLA clock for takedown regardless of API availability.
        """
        if not content_id:
            raise ValueError("content_id is required")
        if not evidence_description:
            raise ValueError("evidence_description is required")

        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=TAKEDOWN_SLA_HOURS)

        # Track takedown SLA
        self._pending_takedowns[content_id] = {
            "deadline": deadline,
            "category": category,
            "submitted_at": now,
            "taken_down": False,
            "evidence": evidence_description,
        }

        if not self._api_key:
            logger.warning("esafety_no_api_key", content_id=content_id)
            return ESafetyComplaint(
                complaint_id=f"local-{content_id}",
                category=category,
                content_id=content_id,
                submitted_at=now,
                status="pending",
                takedown_deadline=deadline,
            )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self._api_url}/complaints",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "category": category.value,
                        "contentId": content_id,
                        "evidence": evidence_description,
                        "reporter": reporter_info or {},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            complaint_id = data.get("complaintId", f"esafety-{content_id}")
            logger.info("esafety_complaint_submitted", complaint_id=complaint_id)

            return ESafetyComplaint(
                complaint_id=complaint_id,
                category=category,
                content_id=content_id,
                submitted_at=now,
                status="submitted",
                takedown_deadline=deadline,
            )
        except Exception as e:
            logger.error("esafety_complaint_failed", error=str(e))
            return ESafetyComplaint(
                complaint_id=None,
                category=category,
                content_id=content_id,
                submitted_at=now,
                status="failed",
                takedown_deadline=deadline,
                error=str(e),
            )

    def mark_taken_down(self, content_id: str) -> bool:
        """Mark content as taken down (stops SLA clock).

        Returns True if content was found and marked, False otherwise.
        """
        if content_id not in self._pending_takedowns:
            logger.warning("esafety_takedown_not_found", content_id=content_id)
            return False

        if self._pending_takedowns[content_id]["taken_down"]:
            logger.info("esafety_already_taken_down", content_id=content_id)
            return True

        self._pending_takedowns[content_id]["taken_down"] = True
        self._pending_takedowns[content_id]["taken_down_at"] = datetime.now(timezone.utc)
        logger.info("esafety_content_taken_down", content_id=content_id)
        return True

    def get_takedown_status(self, content_id: str) -> TakedownStatus | None:
        """Check SLA status for a pending takedown."""
        info = self._pending_takedowns.get(content_id)
        if not info:
            return None

        now = datetime.now(timezone.utc)
        deadline = info["deadline"]

        return TakedownStatus(
            content_id=content_id,
            deadline=deadline,
            is_overdue=now > deadline and not info["taken_down"],
            time_remaining_seconds=max(0, (deadline - now).total_seconds()),
            taken_down=info["taken_down"],
            taken_down_at=info.get("taken_down_at"),
        )

    def get_overdue_takedowns(self) -> list[TakedownStatus]:
        """Get all overdue takedowns (SLA breached)."""
        results = []
        now = datetime.now(timezone.utc)
        for content_id, info in self._pending_takedowns.items():
            if now > info["deadline"] and not info["taken_down"]:
                results.append(TakedownStatus(
                    content_id=content_id,
                    deadline=info["deadline"],
                    is_overdue=True,
                    time_remaining_seconds=0,
                    taken_down=False,
                ))
        return results

    def get_sla_dashboard(self) -> dict:
        """Get SLA dashboard metrics."""
        total = len(self._pending_takedowns)
        taken_down = sum(1 for v in self._pending_takedowns.values() if v["taken_down"])
        overdue = len(self.get_overdue_takedowns())
        pending = total - taken_down - overdue

        return {
            "total_complaints": total,
            "taken_down": taken_down,
            "pending": pending,
            "overdue": overdue,
            "sla_compliance_rate": (taken_down / total * 100) if total > 0 else 100.0,
        }

    def get_all_takedowns(self) -> list[TakedownStatus]:
        """Get status of all tracked takedowns."""
        results = []
        for content_id in self._pending_takedowns:
            status = self.get_takedown_status(content_id)
            if status:
                results.append(status)
        return results


pipeline = ESafetyPipeline()
