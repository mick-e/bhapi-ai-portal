"""State compliance framework — extensible registry for multi-state AI regulations.

Provides an in-memory registry pattern for tracking state-level AI compliance
requirements. Pre-registers OH (active Jul 1 2026) and CA/TX/FL/NY as 2027 prep.

Usage:
    framework = StateComplianceFramework()  # preload=True by default
    result = framework.check_compliance(["OH", "CA"], satisfied_requirements=["ai_usage"])
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import structlog

from src.exceptions import BhapiException, NotFoundError

logger = structlog.get_logger()


class StateNotRegisteredError(NotFoundError):
    """Raised when a state code is not found in the registry."""

    def __init__(self, state_code: str):
        super().__init__("State regulation", state_code)


class StateAlreadyRegisteredError(BhapiException):
    """Raised when attempting to register a state that already exists."""

    def __init__(self, state_code: str):
        super().__init__(
            message=f"State '{state_code}' is already registered",
            code="CONFLICT",
            status_code=409,
        )


class StateComplianceFramework:
    """Extensible registry for state-level AI compliance requirements.

    Supports registering new state regulations, checking compliance across
    multiple states, and tracking upcoming deadlines.
    """

    def __init__(self, *, preload: bool = True) -> None:
        self._registry: dict[str, dict] = {}
        if preload:
            self._preload_states()

    def _preload_states(self) -> None:
        """Pre-register known state regulations."""
        # Ohio — active mandate, effective Jul 1 2026
        self.register_state(
            code="OH",
            name="Ohio AI Mandate (HB 319)",
            effective_date=date(2026, 7, 1),
            requirements=[
                "ai_usage",
                "tool_inventory",
                "risk_assessment",
                "governance",
            ],
        )
        # 2027 prep states
        self.register_state(
            code="CA",
            name="California AI Transparency Act",
            effective_date=date(2027, 1, 1),
            requirements=[
                "ai_disclosure",
                "risk_assessment",
                "data_governance",
            ],
        )
        self.register_state(
            code="TX",
            name="Texas AI Safety in Education Act",
            effective_date=date(2027, 6, 1),
            requirements=[
                "ai_usage",
                "tool_inventory",
                "parental_notification",
            ],
        )
        self.register_state(
            code="FL",
            name="Florida Digital Classroom Safety Act",
            effective_date=date(2027, 7, 1),
            requirements=[
                "ai_usage",
                "risk_assessment",
                "governance",
                "data_governance",
            ],
        )
        self.register_state(
            code="NY",
            name="New York AI in Education Act",
            effective_date=date(2027, 9, 1),
            requirements=[
                "ai_usage",
                "governance",
                "equity_assessment",
            ],
        )

        logger.info(
            "state_framework_preloaded",
            state_count=len(self._registry),
            states=list(self._registry.keys()),
        )

    def register_state(
        self,
        *,
        code: str,
        name: str,
        effective_date: date,
        requirements: list[str],
    ) -> None:
        """Register a new state regulation.

        Args:
            code: Two-letter state code (e.g. "CA"). Normalized to uppercase.
            name: Human-readable regulation name.
            effective_date: Date the regulation takes effect.
            requirements: List of required policy types (e.g. ["ai_usage", "governance"]).

        Raises:
            ValueError: If code or name is empty.
            StateAlreadyRegisteredError: If the state code is already registered.
        """
        if not code or not code.strip():
            raise ValueError("state code is required")
        if not name or not name.strip():
            raise ValueError("name is required")

        normalized = code.strip().upper()

        if normalized in self._registry:
            raise StateAlreadyRegisteredError(normalized)

        self._registry[normalized] = {
            "code": normalized,
            "name": name.strip(),
            "effective_date": effective_date,
            "requirements": list(requirements),
            "registered_at": datetime.now(timezone.utc),
        }

        logger.info(
            "state_registered",
            code=normalized,
            name=name,
            effective_date=str(effective_date),
            requirement_count=len(requirements),
        )

    def get_registered_states(self) -> list[str]:
        """Return all registered state codes, sorted alphabetically."""
        return sorted(self._registry.keys())

    def get_state_config(self, code: str) -> dict:
        """Get the full configuration for a registered state.

        Args:
            code: Two-letter state code.

        Returns:
            Dict with code, name, effective_date, requirements, registered_at.

        Raises:
            StateNotRegisteredError: If the state is not registered.
        """
        normalized = code.strip().upper()
        if normalized not in self._registry:
            raise StateNotRegisteredError(normalized)
        return dict(self._registry[normalized])

    def check_compliance(
        self,
        state_codes: list[str],
        satisfied_requirements: list[str],
    ) -> dict[str, dict]:
        """Check compliance across multiple states simultaneously.

        Args:
            state_codes: List of state codes to check.
            satisfied_requirements: List of requirement keys already satisfied.

        Returns:
            Dict mapping state code to {status, met, missing, effective_date}.
            status is "compliant", "partial", or "non_compliant".

        Raises:
            StateNotRegisteredError: If any state code is not registered.
        """
        if not state_codes:
            return {}

        satisfied_set = set(satisfied_requirements)
        result: dict[str, dict] = {}

        for code in state_codes:
            normalized = code.strip().upper()
            if normalized not in self._registry:
                raise StateNotRegisteredError(normalized)

            config = self._registry[normalized]
            required = config["requirements"]
            met = [r for r in required if r in satisfied_set]
            missing = [r for r in required if r not in satisfied_set]

            if not missing:
                status = "compliant"
            elif met:
                status = "partial"
            else:
                status = "non_compliant"

            result[normalized] = {
                "status": status,
                "met": met,
                "missing": missing,
                "effective_date": config["effective_date"],
                "name": config["name"],
            }

        logger.info(
            "compliance_checked",
            states=list(result.keys()),
            results={k: v["status"] for k, v in result.items()},
        )

        return result

    def is_active(self, code: str) -> bool:
        """Check if a state's regulation is currently in effect.

        Args:
            code: Two-letter state code.

        Returns:
            True if today >= effective_date.

        Raises:
            StateNotRegisteredError: If the state is not registered.
        """
        config = self.get_state_config(code)
        return date.today() >= config["effective_date"]

    def get_upcoming_deadlines(self) -> list[dict]:
        """Get all registered states sorted by effective date.

        Returns:
            List of dicts with code, name, effective_date, is_active.
        """
        deadlines = []
        for config in self._registry.values():
            deadlines.append({
                "code": config["code"],
                "name": config["name"],
                "effective_date": config["effective_date"],
                "is_active": date.today() >= config["effective_date"],
            })
        deadlines.sort(key=lambda d: d["effective_date"])
        return deadlines
