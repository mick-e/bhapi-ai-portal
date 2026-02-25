"""OpenAI spend polling client.

Fetches usage data from the OpenAI /usage endpoint (or /organization/costs
for the newer API). Normalizes into SpendEntry objects.
"""

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


class OpenAIProvider(BaseProvider):
    """OpenAI usage/billing API client."""

    provider_name = "openai"
    _BASE_URL = "https://api.openai.com/v1"

    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch OpenAI usage data for the given date range.

        Uses the /organization/costs endpoint (newer) or falls back to
        /usage endpoint for daily breakdowns.
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        entries: list[SpendEntry] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try the organization costs endpoint first
                response = await client.get(
                    f"{self._BASE_URL}/organization/costs",
                    headers=headers,
                    params={
                        "start_time": int(start_date.timestamp()),
                        "end_time": int(end_date.timestamp()),
                        "group_by": ["line_item"],
                    },
                )

                if response.status_code == 401:
                    raise AuthenticationError("Invalid OpenAI API key")
                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", "60"))
                    raise RateLimitError("OpenAI rate limit hit", retry_after=retry_after)

                if response.status_code == 200:
                    data = response.json()
                    entries = self._parse_costs_response(data, start_date, end_date)
                elif response.status_code == 404:
                    # Fallback: older /usage endpoint
                    entries = await self._fetch_usage_legacy(
                        client, headers, start_date, end_date
                    )
                else:
                    logger.warning(
                        "openai_unexpected_status",
                        status=response.status_code,
                        body=response.text[:200],
                    )

        except (AuthenticationError, RateLimitError):
            raise
        except httpx.HTTPError as exc:
            logger.error("openai_fetch_error", error=str(exc))

        logger.info(
            "openai_usage_fetched",
            entries=len(entries),
            period=f"{start_date.date()} to {end_date.date()}",
        )
        return entries

    async def validate_credentials(self) -> bool:
        """Validate the OpenAI API key by making a lightweight request."""
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

    def _parse_costs_response(
        self,
        data: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Parse the /organization/costs response."""
        entries: list[SpendEntry] = []
        results = data.get("data", [])

        for bucket in results:
            amount = bucket.get("results", [{}])
            for item in amount:
                cost_cents = item.get("amount", {}).get("value", 0)
                cost_usd = cost_cents / 100.0 if cost_cents else 0.0

                if cost_usd <= 0:
                    continue

                entries.append(
                    SpendEntry(
                        amount=round(cost_usd, 6),
                        currency="USD",
                        period_start=start_date,
                        period_end=end_date,
                        model=item.get("line_item", "unknown"),
                        token_count=None,
                        raw_data=item,
                    )
                )

        return entries

    async def _fetch_usage_legacy(
        self,
        client,
        headers: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fallback: fetch from the /usage endpoint (daily aggregation)."""
        entries: list[SpendEntry] = []

        response = await client.get(
            f"{self._BASE_URL}/usage",
            headers=headers,
            params={
                "date": start_date.strftime("%Y-%m-%d"),
            },
        )

        if response.status_code == 200:
            data = response.json()
            for day_data in data.get("data", []):
                # Sum up the whisper + dall-e + etc. costs
                total_cost = sum(
                    item.get("cost", 0) for item in day_data.get("line_items", [day_data])
                )
                if total_cost > 0:
                    entries.append(
                        SpendEntry(
                            amount=round(total_cost / 100.0, 6),
                            currency="USD",
                            period_start=start_date,
                            period_end=end_date,
                            raw_data=day_data,
                        )
                    )

        return entries
