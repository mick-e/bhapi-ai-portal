"""Spend sync scheduler — hourly job that syncs all active LLM accounts.

For each active LLMAccount, fetches usage from the provider API and creates
SpendRecord rows. Handles individual errors per account so one failure
doesn't block others.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import LLMAccount, SpendRecord
from src.billing.providers.base import (
    AuthenticationError,
    BaseProvider,
    RateLimitError,
)

logger = structlog.get_logger()

# Provider registry — maps provider name to provider class
_PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {}


def register_provider(name: str, provider_class: type[BaseProvider]) -> None:
    """Register a provider class for a given provider name."""
    _PROVIDER_REGISTRY[name] = provider_class


def _init_registry() -> None:
    """Initialize the provider registry with all known providers."""
    if _PROVIDER_REGISTRY:
        return

    from src.billing.providers.anthropic_client import AnthropicProvider
    from src.billing.providers.google_client import GoogleProvider
    from src.billing.providers.microsoft_client import MicrosoftProvider
    from src.billing.providers.openai_client import OpenAIProvider

    register_provider("openai", OpenAIProvider)
    register_provider("anthropic", AnthropicProvider)
    register_provider("google", GoogleProvider)
    register_provider("microsoft", MicrosoftProvider)

    from src.billing.providers.xai_client import XAIProvider
    register_provider("xai", XAIProvider)


def get_provider(name: str, api_key: str) -> BaseProvider:
    """Get a provider instance by name."""
    _init_registry()
    provider_class = _PROVIDER_REGISTRY.get(name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}")
    return provider_class(api_key)


async def sync_all_accounts(db: AsyncSession) -> dict:
    """Sync spend for all active LLM accounts.

    Returns a summary dict with counts of synced, errored, and skipped accounts.
    """
    result = await db.execute(
        select(LLMAccount).where(LLMAccount.status == "active")
    )
    accounts = list(result.scalars().all())

    summary = {"total": len(accounts), "synced": 0, "errored": 0, "skipped": 0}

    for account in accounts:
        try:
            count = await sync_account(db, account)
            summary["synced"] += 1
            logger.info(
                "account_synced",
                account_id=str(account.id),
                provider=account.provider,
                records=count,
            )
        except Exception as exc:
            summary["errored"] += 1
            logger.error(
                "account_sync_error",
                account_id=str(account.id),
                provider=account.provider,
                error=str(exc),
            )
            # Mark account as error state for auth failures
            if isinstance(exc, AuthenticationError):
                account.status = "error"

    await db.flush()

    logger.info("spend_sync_completed", **summary)
    return summary


async def sync_account(
    db: AsyncSession,
    account: LLMAccount,
) -> int:
    """Sync spend for a single LLM account.

    Fetches usage since last sync (or last 24 hours if first sync).
    Returns the number of SpendRecord entries created.
    """
    if not account.credentials_encrypted:
        logger.debug("sync_skip_no_credentials", account_id=str(account.id))
        return 0

    # Determine sync window
    now = datetime.now(timezone.utc)
    if account.last_synced:
        start = account.last_synced
    else:
        start = now - timedelta(hours=24)

    provider = get_provider(account.provider, account.credentials_encrypted)

    try:
        entries = await provider.fetch_usage(start, now)
    except RateLimitError as exc:
        logger.warning(
            "sync_rate_limited",
            account_id=str(account.id),
            retry_after=exc.retry_after,
        )
        return 0

    # Create SpendRecord rows
    created = 0
    for entry in entries:
        record = SpendRecord(
            id=uuid4(),
            group_id=account.group_id,
            llm_account_id=account.id,
            member_id=entry.member_id,
            period_start=entry.period_start or start,
            period_end=entry.period_end or now,
            amount=entry.amount,
            currency=entry.currency,
            token_count=entry.token_count,
            model=entry.model,
            raw_data=entry.raw_data,
        )
        db.add(record)
        created += 1

    # Update last_synced timestamp
    account.last_synced = now
    await db.flush()

    return created
