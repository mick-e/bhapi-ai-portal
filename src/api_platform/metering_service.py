"""Metering service — tier assignment, quota checks, usage recording."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.tiers import FREE_TIER, TIERS, APITier
from src.api_platform.usage_metering import (
    APIKeyRateTier,
    APIRequestLog,
    MonthlyUsageAggregate,
)

logger = structlog.get_logger()


def _current_year_month() -> str:
    """Return the current year-month string, e.g. '2026-04'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def get_key_tier(db: AsyncSession, api_key_id: UUID) -> APITier:
    """Look up the rate tier for an API key. Defaults to free tier."""
    result = await db.execute(
        select(APIKeyRateTier).where(APIKeyRateTier.api_key_id == api_key_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        return FREE_TIER

    tier_name = mapping.tier_name
    return TIERS.get(tier_name, FREE_TIER)


async def assign_tier(db: AsyncSession, api_key_id: UUID, tier_name: str) -> APIKeyRateTier:
    """Assign (or update) the rate tier for an API key.

    Raises ValueError if tier_name is unknown.
    """
    if tier_name not in TIERS:
        raise ValueError(f"Unknown API tier: {tier_name}")

    result = await db.execute(
        select(APIKeyRateTier).where(APIKeyRateTier.api_key_id == api_key_id)
    )
    mapping = result.scalar_one_or_none()

    if mapping:
        mapping.tier_name = tier_name
    else:
        mapping = APIKeyRateTier(
            id=uuid4(),
            api_key_id=api_key_id,
            tier_name=tier_name,
        )
        db.add(mapping)

    await db.flush()
    logger.info("api_key_tier_assigned", api_key_id=str(api_key_id), tier=tier_name)
    return mapping


async def get_monthly_usage(
    db: AsyncSession,
    api_key_id: UUID,
    year_month: str | None = None,
) -> int:
    """Get the total request count for an API key in a given month.

    Defaults to the current month.
    """
    ym = year_month or _current_year_month()
    result = await db.execute(
        select(MonthlyUsageAggregate.request_count).where(
            MonthlyUsageAggregate.api_key_id == api_key_id,
            MonthlyUsageAggregate.year_month == ym,
        )
    )
    count = result.scalar_one_or_none()
    return count or 0


async def check_quota(db: AsyncSession, api_key_id: UUID, tier: APITier | None = None) -> bool:
    """Check whether the API key is within its monthly quota.

    Returns True if within quota, False if exceeded.
    """
    if tier is None:
        tier = await get_key_tier(db, api_key_id)

    usage = await get_monthly_usage(db, api_key_id)
    return usage < tier.monthly_request_quota


async def record_usage(
    db: AsyncSession,
    api_key_id: UUID,
    endpoint: str,
    status_code: int,
    response_time_ms: int = 0,
) -> None:
    """Record an API request and update the monthly aggregate."""
    # Insert per-request log
    log = APIRequestLog(
        id=uuid4(),
        api_key_id=api_key_id,
        endpoint=endpoint,
        status_code=status_code,
        response_time_ms=response_time_ms,
    )
    db.add(log)

    # Upsert monthly aggregate
    ym = _current_year_month()
    result = await db.execute(
        select(MonthlyUsageAggregate).where(
            MonthlyUsageAggregate.api_key_id == api_key_id,
            MonthlyUsageAggregate.year_month == ym,
        )
    )
    agg = result.scalar_one_or_none()

    if agg:
        # Update running average
        old_total = agg.avg_response_time_ms * agg.request_count
        agg.request_count += 1
        if status_code >= 400:
            agg.error_count += 1
        agg.avg_response_time_ms = (old_total + response_time_ms) / agg.request_count
    else:
        agg = MonthlyUsageAggregate(
            id=uuid4(),
            api_key_id=api_key_id,
            year_month=ym,
            request_count=1,
            error_count=1 if status_code >= 400 else 0,
            avg_response_time_ms=float(response_time_ms),
        )
        db.add(agg)

    await db.flush()


async def get_usage_stats(
    db: AsyncSession,
    api_key_id: UUID,
    year_month: str | None = None,
) -> dict:
    """Get detailed usage statistics for an API key.

    Returns a dict with request_count, error_count, avg_response_time_ms,
    quota_limit, quota_remaining, and tier info.
    """
    tier = await get_key_tier(db, api_key_id)
    ym = year_month or _current_year_month()

    result = await db.execute(
        select(MonthlyUsageAggregate).where(
            MonthlyUsageAggregate.api_key_id == api_key_id,
            MonthlyUsageAggregate.year_month == ym,
        )
    )
    agg = result.scalar_one_or_none()

    request_count = agg.request_count if agg else 0
    error_count = agg.error_count if agg else 0
    avg_response_time_ms = agg.avg_response_time_ms if agg else 0.0

    return {
        "api_key_id": str(api_key_id),
        "year_month": ym,
        "tier": tier.name,
        "request_count": request_count,
        "error_count": error_count,
        "avg_response_time_ms": round(avg_response_time_ms, 2),
        "quota_limit": tier.monthly_request_quota,
        "quota_remaining": max(0, tier.monthly_request_quota - request_count),
        "requests_per_minute": tier.requests_per_minute,
        "webhooks_enabled": tier.webhooks_enabled,
        "sandbox_only": tier.sandbox_only,
    }
