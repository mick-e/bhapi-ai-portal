"""API Platform — OAuth 2.0 B2B API for partners and schools.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

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

__all__ = [
    "approve_client",
    "get_client",
    "get_client_by_client_id",
    "get_usage",
    "list_clients",
    "list_tiers",
    "record_usage",
    "register_client",
]
