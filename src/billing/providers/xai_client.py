"""xAI (Grok) spend polling client."""

from __future__ import annotations

from datetime import datetime

import structlog

from src.billing.providers.base import (
    AuthenticationError,
    BaseProvider,
    RateLimitError,
    SpendEntry,
)

logger = structlog.get_logger()


class XAIProvider(BaseProvider):
    """xAI usage/billing API client."""

    provider_name = "xai"
    _BASE_URL = "https://api.x.ai/v1"

    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch xAI usage data for the given date range."""
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        entries: list[SpendEntry] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self._BASE_URL}/organization/usage",
                    headers=headers,
                    params={
                        "start_time": int(start_date.timestamp()),
                        "end_time": int(end_date.timestamp()),
                    },
                )

                if response.status_code == 401:
                    raise AuthenticationError("Invalid xAI API key")
                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", "60"))
                    raise RateLimitError("xAI rate limit hit", retry_after=retry_after)

                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("data", []):
                        cost = item.get("cost", 0.0)
                        if cost > 0:
                            entries.append(
                                SpendEntry(
                                    amount=round(cost, 6),
                                    currency="USD",
                                    period_start=start_date,
                                    period_end=end_date,
                                    model=item.get("model", "grok"),
                                    token_count=item.get("total_tokens"),
                                    raw_data=item,
                                )
                            )

        except (AuthenticationError, RateLimitError):
            raise
        except httpx.HTTPError as exc:
            logger.error("xai_fetch_error", error=str(exc))

        logger.info("xai_usage_fetched", entries=len(entries))
        return entries

    async def validate_credentials(self) -> bool:
        """Validate the xAI API key."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False
