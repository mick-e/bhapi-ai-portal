"""API Platform — OAuth 2.0 B2B API for partners and schools.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.api_platform.metering_service import (
    assign_tier as assign_key_tier,
    check_quota,
    get_key_tier,
    get_monthly_usage,
    get_usage_stats,
    record_usage as record_metered_usage,
)
from src.api_platform.service import (
    approve_client,
    get_client,
    get_client_by_client_id,
    get_usage,
    list_clients,
    list_tiers,
    record_usage,
    register_client,
)
from src.api_platform.tiers import (
    BUSINESS_TIER,
    DEVELOPER_TIER,
    ENTERPRISE_TIER,
    FREE_TIER,
    TIERS,
    APITier,
    get_tier,
)
from src.api_platform.usage_metering import (
    APIKeyRateTier,
    APIRequestLog,
    MonthlyUsageAggregate,
)

__all__ = [
    # Existing service functions
    "approve_client",
    "get_client",
    "get_client_by_client_id",
    "get_usage",
    "list_clients",
    "list_tiers",
    "record_usage",
    "register_client",
    # Tier definitions
    "APITier",
    "TIERS",
    "get_tier",
    "FREE_TIER",
    "DEVELOPER_TIER",
    "BUSINESS_TIER",
    "ENTERPRISE_TIER",
    # Usage metering models
    "APIKeyRateTier",
    "APIRequestLog",
    "MonthlyUsageAggregate",
    # Metering service functions
    "assign_key_tier",
    "check_quota",
    "get_key_tier",
    "get_monthly_usage",
    "get_usage_stats",
    "record_metered_usage",
]
