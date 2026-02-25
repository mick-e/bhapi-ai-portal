"""Microsoft Azure Cost Management spend polling client.

Fetches Azure OpenAI / Copilot usage data from the Azure Cost Management API.
Normalizes into SpendEntry objects.
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


class MicrosoftProvider(BaseProvider):
    """Azure Cost Management API client for Azure OpenAI spend."""

    provider_name = "microsoft"
    _BASE_URL = "https://management.azure.com"

    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch Azure Cost Management data for the given date range.

        Queries the Cost Management API for Azure OpenAI service costs.
        The api_key is expected to be a Bearer token from Azure AD.
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        entries: list[SpendEntry] = []

        # Azure Cost Management query payload
        query_body = {
            "type": "ActualCost",
            "timeframe": "Custom",
            "timePeriod": {
                "from": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "to": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {
                    "totalCost": {"name": "Cost", "function": "Sum"},
                },
                "filter": {
                    "dimensions": {
                        "name": "ServiceName",
                        "operator": "In",
                        "values": ["Azure OpenAI", "Cognitive Services"],
                    }
                },
                "grouping": [
                    {"type": "Dimension", "name": "MeterCategory"},
                ],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._BASE_URL}/providers/Microsoft.CostManagement/query"
                    "?api-version=2023-11-01",
                    headers=headers,
                    json=query_body,
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AuthenticationError("Invalid Azure credentials")
                if response.status_code == 429:
                    retry_after = int(response.headers.get("x-ms-ratelimit-remaining-subscription-reads", "60"))
                    raise RateLimitError("Azure rate limit hit", retry_after=retry_after)

                if response.status_code == 200:
                    data = response.json()
                    entries = self._parse_response(data, start_date, end_date)
                else:
                    logger.warning(
                        "azure_unexpected_status",
                        status=response.status_code,
                        body=response.text[:200],
                    )

        except (AuthenticationError, RateLimitError):
            raise
        except Exception as exc:
            logger.error("azure_fetch_error", error=str(exc))

        logger.info(
            "azure_usage_fetched",
            entries=len(entries),
            period=f"{start_date.date()} to {end_date.date()}",
        )
        return entries

    async def validate_credentials(self) -> bool:
        """Validate Azure credentials."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._BASE_URL}/subscriptions?api-version=2022-12-01",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

    def _parse_response(
        self,
        data: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Parse the Azure Cost Management query response."""
        entries: list[SpendEntry] = []

        rows = data.get("properties", {}).get("rows", [])
        columns = data.get("properties", {}).get("columns", [])

        # Find column indices
        cost_idx = next(
            (i for i, c in enumerate(columns) if c.get("name") == "Cost"), 0
        )
        category_idx = next(
            (i for i, c in enumerate(columns) if c.get("name") == "MeterCategory"), 1
        )

        for row in rows:
            cost = float(row[cost_idx]) if len(row) > cost_idx else 0.0
            category = row[category_idx] if len(row) > category_idx else "unknown"

            if cost <= 0:
                continue

            entries.append(
                SpendEntry(
                    amount=round(cost, 6),
                    currency="USD",
                    period_start=start_date,
                    period_end=end_date,
                    model=category,
                    raw_data={"row": row, "columns": [c.get("name") for c in columns]},
                )
            )

        return entries
