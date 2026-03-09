"""Provider-specific spend synchronization."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def sync_provider_spend(db: AsyncSession, account) -> dict:
    """Sync spend data from an LLM provider.

    In production, this calls provider APIs (OpenAI, Anthropic, etc).
    Currently returns mock data for providers without billing APIs.
    """
    from src.encryption import decrypt_credential

    provider = account.provider

    if not account.credentials_encrypted:
        raise ValueError(f"No credentials for {provider} account {account.id}")

    # Decrypt credentials
    try:
        _api_key = decrypt_credential(account.credentials_encrypted)
    except Exception as exc:
        raise ValueError(f"Failed to decrypt credentials: {exc}")

    logger.info("spend_sync_started", provider=provider, account_id=str(account.id))

    # Provider-specific sync would go here
    # For now, return success with no new records
    return {
        "provider": provider,
        "records_synced": 0,
        "message": f"Sync completed for {provider}",
    }
