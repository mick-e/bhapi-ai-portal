"""Anonymization utilities for intelligence network signals.

Implements k-anonymity, differential privacy (Laplace mechanism),
and identifier hashing to ensure no PII leaks into shared signals.
"""

import hashlib
import math
import random
from collections import Counter
from datetime import datetime, timezone
from typing import Any


# PII field names that MUST be stripped from any signal before sharing.
_PII_FIELDS = frozenset({
    "user_id",
    "email",
    "member_id",
    "name",
    "display_name",
    "first_name",
    "last_name",
    "phone",
    "ip_address",
    "device_id",
})


def k_anonymize(
    records: list[dict[str, Any]],
    quasi_identifiers: list[str],
    k: int = 5,
) -> list[dict[str, Any]]:
    """Generalize quasi-identifiers so each combination appears >= k times.

    Records whose quasi-identifier group has fewer than *k* members are
    dropped to prevent re-identification.

    Args:
        records: List of dicts to anonymize.
        quasi_identifiers: Field names to treat as quasi-identifiers.
        k: Minimum group size (default 5).

    Returns:
        Filtered list with only groups of size >= k.
    """
    if not records or not quasi_identifiers:
        return records

    # Group records by quasi-identifier values
    groups: dict[tuple, list[dict]] = {}
    for rec in records:
        key = tuple(rec.get(qi) for qi in quasi_identifiers)
        groups.setdefault(key, []).append(rec)

    # Keep only groups meeting the k threshold
    result = []
    for group_records in groups.values():
        if len(group_records) >= k:
            result.extend(group_records)

    return result


def add_dp_noise(value: float, epsilon: float = 1.0) -> float:
    """Add Laplace noise for differential privacy.

    Uses the Laplace mechanism with sensitivity = 1.

    Args:
        value: The true numeric value.
        epsilon: Privacy budget (smaller = more private, default 1.0).

    Returns:
        Noised value rounded to 2 decimal places.
    """
    if epsilon <= 0:
        raise ValueError("Epsilon must be positive")

    scale = 1.0 / epsilon
    # Laplace noise via inverse CDF: b * sign(u) * ln(1 - 2|u|) where u ~ Uniform(-0.5, 0.5)
    u = random.random() - 0.5
    noise = -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
    return round(value + noise, 2)


def hash_identifier(value: str, salt: str = "") -> str:
    """One-way SHA-256 hash of an identifier.

    Args:
        value: The identifier to hash.
        salt: Optional salt for domain separation.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()


def _coarsen_location(location: str | None) -> str | None:
    """Coarsen location to country-level only.

    Strips city, region, postal code — keeps only the last comma-separated
    segment (assumed to be the country) or returns the whole string if
    there is no comma.
    """
    if not location:
        return None
    parts = [p.strip() for p in location.split(",")]
    # Return the last part (country)
    return parts[-1] if parts else None


def _coarsen_timestamp(ts: datetime | str | None) -> str | None:
    """Generalize a timestamp to hour-of-day (strips exact minute/second/date)."""
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return None
    return f"{ts.hour:02d}:00"


def anonymize_signal(raw_event: dict[str, Any]) -> dict[str, Any]:
    """Anonymize a raw event for sharing on the intelligence network.

    Strips all PII fields, coarsens location to country-level,
    and generalizes timestamps to hour-of-day.

    Args:
        raw_event: The raw event dict (may contain PII).

    Returns:
        A new dict with PII removed and quasi-identifiers generalized.
    """
    result: dict[str, Any] = {}
    stripped_fields: list[str] = []

    for key, value in raw_event.items():
        # Strip PII fields
        if key.lower() in _PII_FIELDS:
            stripped_fields.append(key)
            continue

        # Coarsen location
        if key.lower() in ("location", "region", "city"):
            if key.lower() == "location":
                result["contributor_region"] = _coarsen_location(value)
            stripped_fields.append(key)
            continue

        # Generalize timestamps
        if key.lower() in ("timestamp", "created_at", "occurred_at"):
            result["time_of_day"] = _coarsen_timestamp(value)
            stripped_fields.append(key)
            continue

        result[key] = value

    result["_stripped_fields"] = stripped_fields
    return result
