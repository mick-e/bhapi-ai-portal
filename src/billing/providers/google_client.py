"""Google Cloud Billing API spend polling client.

Fetches usage data from Google Cloud Billing API for Vertex AI / Gemini
API spend tracking. Normalizes into SpendEntry objects.
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


class GoogleProvider(BaseProvider):
    """Google Cloud Billing API client for Vertex AI spend."""

    provider_name = "google"
    _BASE_URL = "https://cloudbilling.googleapis.com/v1"

    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch Google Cloud spend data for the given date range.

        Uses the Cloud Billing API to get Vertex AI / Gemini API costs.
        The api_key here is expected to be a service account JSON key or
        an OAuth access token.
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        entries: list[SpendEntry] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use the BigQuery billing export or CostManagement API
                # For simplicity, we query the budgets/costs endpoint
                response = await client.get(
                    f"{self._BASE_URL}/billingAccounts/-/costs",
                    headers=headers,
                    params={
                        "filter": (
                            f'usage_start_time>="{start_date.strftime("%Y-%m-%dT%H:%M:%SZ")}" '
                            f'AND usage_end_time<="{end_date.strftime("%Y-%m-%dT%H:%M:%SZ")}" '
                            'AND service.description="Vertex AI"'
                        ),
                    },
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise AuthenticationError("Invalid Google Cloud credentials")
                if response.status_code == 429:
                    raise RateLimitError("Google Cloud rate limit hit")

                if response.status_code == 200:
                    data = response.json()
                    entries = self._parse_response(data, start_date, end_date)
                else:
                    logger.warning(
                        "google_unexpected_status",
                        status=response.status_code,
                        body=response.text[:200],
                    )

        except (AuthenticationError, RateLimitError):
            raise
        except httpx.HTTPError as exc:
            logger.error("google_fetch_error", error=str(exc))

        logger.info(
            "google_usage_fetched",
            entries=len(entries),
            period=f"{start_date.date()} to {end_date.date()}",
        )
        return entries

    async def validate_credentials(self) -> bool:
        """Validate Google Cloud credentials."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._BASE_URL}/billingAccounts",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    def _parse_response(
        self,
        data: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Parse the Google Cloud Billing API response."""
        entries: list[SpendEntry] = []

        for item in data.get("costItems", data.get("results", [])):
            cost = item.get("cost", {})
            amount = cost.get("amount", 0.0)
            currency = cost.get("currency", "USD")

            if amount <= 0:
                continue

            entries.append(
                SpendEntry(
                    amount=round(float(amount), 6),
                    currency=currency,
                    period_start=start_date,
                    period_end=end_date,
                    model=item.get("sku", {}).get("description", "vertex-ai"),
                    raw_data=item,
                )
            )

        return entries
