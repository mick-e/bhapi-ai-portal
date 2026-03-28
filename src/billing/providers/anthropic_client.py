"""Anthropic spend polling client.

Fetches usage data from the Anthropic API. Normalizes into SpendEntry objects.
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


class AnthropicProvider(BaseProvider):
    """Anthropic usage/billing API client."""

    provider_name = "anthropic"
    _BASE_URL = "https://api.anthropic.com/v1"

    async def fetch_usage(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Fetch Anthropic usage data for the given date range.

        Uses the /usage endpoint with API key authentication.
        Handles pagination via cursor-based next_page tokens.
        """
        import httpx

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        entries: list[SpendEntry] = []
        page_id: str | None = None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while True:
                    params: dict = {
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                    }
                    if page_id:
                        params["page"] = page_id

                    response = await client.get(
                        f"{self._BASE_URL}/usage",
                        headers=headers,
                        params=params,
                    )

                    if response.status_code == 401:
                        raise AuthenticationError("Invalid Anthropic API key")
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("retry-after", "60"))
                        raise RateLimitError(
                            "Anthropic rate limit hit", retry_after=retry_after
                        )

                    if response.status_code != 200:
                        logger.warning(
                            "anthropic_unexpected_status",
                            status=response.status_code,
                            body=response.text[:200],
                        )
                        break

                    data = response.json()
                    entries.extend(self._parse_usage_response(data, start_date, end_date))

                    # Handle pagination
                    page_id = data.get("next_page")
                    if not page_id:
                        break

        except (AuthenticationError, RateLimitError):
            raise
        except httpx.HTTPError as exc:
            logger.error("anthropic_fetch_error", error=str(exc))

        logger.info(
            "anthropic_usage_fetched",
            entries=len(entries),
            period=f"{start_date.date()} to {end_date.date()}",
        )
        return entries

    async def validate_credentials(self) -> bool:
        """Validate the Anthropic API key."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._BASE_URL}/models",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def revoke_key(self) -> bool:
        """Revoke Anthropic API key via the admin API.

        Uses DELETE /v1/api_keys/{key_id} to deactivate the key.
        Requires an admin-scoped API key to perform revocation.
        """
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }
                # List keys to find the matching one
                response = await client.get(
                    f"{self._BASE_URL}/api_keys",
                    headers=headers,
                )
                if response.status_code != 200:
                    logger.warning("anthropic_revoke_list_failed", status=response.status_code)
                    return False

                keys = response.json().get("data", [])
                key_prefix = self.api_key[:12] if len(self.api_key) >= 12 else self.api_key
                target_key = next(
                    (k for k in keys if k.get("partial_key_hint", "").startswith(key_prefix[:8])),
                    None,
                )
                if not target_key:
                    logger.warning("anthropic_revoke_key_not_found")
                    return False

                # Disable the key
                del_response = await client.post(
                    f"{self._BASE_URL}/api_keys/{target_key['id']}/disable",
                    headers=headers,
                )
                if del_response.status_code in (200, 204):
                    logger.info("anthropic_key_revoked", key_id=target_key["id"])
                    return True

                logger.warning("anthropic_revoke_failed", status=del_response.status_code)
                return False
        except httpx.HTTPError as exc:
            logger.error("anthropic_revoke_error", error=str(exc))
            return False

    def _parse_usage_response(
        self,
        data: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[SpendEntry]:
        """Parse the Anthropic /usage response."""
        entries: list[SpendEntry] = []

        for item in data.get("data", []):
            input_tokens = item.get("input_tokens", 0)
            output_tokens = item.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens
            cost_usd = item.get("cost_usd", 0.0)

            if cost_usd <= 0 and total_tokens <= 0:
                continue

            # If cost_usd not provided, estimate from tokens
            if cost_usd <= 0 and total_tokens > 0:
                cost_usd = self._estimate_cost(
                    input_tokens, output_tokens, item.get("model", "")
                )

            entries.append(
                SpendEntry(
                    amount=round(cost_usd, 6),
                    currency="USD",
                    period_start=start_date,
                    period_end=end_date,
                    token_count=total_tokens,
                    model=item.get("model", "unknown"),
                    raw_data=item,
                )
            )

        return entries

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate cost from token counts when API doesn't provide cost_usd.

        Uses approximate pricing tiers. Not perfectly accurate but provides
        a reasonable estimate for tracking purposes.
        """
        # Pricing per 1M tokens (input, output) as of 2025
        pricing = {
            "claude-opus-4": (15.0, 75.0),
            "claude-sonnet-4": (3.0, 15.0),
            "claude-haiku-3.5": (0.80, 4.0),
        }

        # Default to sonnet pricing
        input_rate, output_rate = pricing.get("claude-sonnet-4", (3.0, 15.0))

        # Try to match model name
        model_lower = model.lower()
        for key, rates in pricing.items():
            if key.replace("-", "") in model_lower.replace("-", ""):
                input_rate, output_rate = rates
                break

        cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
        return round(cost, 6)
