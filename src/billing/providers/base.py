"""Abstract base provider for LLM spend polling.

Each provider implements fetch_usage() which returns normalized SpendEntry objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class SpendEntry:
    """Normalized spend entry from any LLM provider."""

    amount: float
    currency: str = "USD"
    period_start: datetime | None = None
    period_end: datetime | None = None
    token_count: int | None = None
    model: str | None = None
    member_id: UUID | None = None
    raw_data: dict = field(default_factory=dict)


class ProviderError(Exception):
    """Base error for provider operations."""


class AuthenticationError(ProviderError):
    """Raised when API credentials are invalid or expired."""


class RateLimitError(ProviderError):
    """Raised when the provider rate-limits our requests."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class BaseProvider(ABC):
    """Abstract base class for LLM spend providers."""

    provider_name: str = "unknown"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch usage/spend data for the given date range.

        Returns normalized SpendEntry objects.
        Raises AuthenticationError if credentials are invalid.
        Raises RateLimitError if rate limited.
        """
        ...

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Check if the stored API key is still valid.

        Returns True if credentials work, False otherwise.
        """
        ...
