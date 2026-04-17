"""Identity-protection partner integration — Family+ Phase 4 Task 22.

Provides a partner-agnostic interface for bundled identity-protection so the
business can swap partners (Aura, IDX, Identity Guard, LifeLock) without
touching call sites. The default implementation is a ``MockPartnerClient``
that succeeds locally and in tests; production deployments select a concrete
client via the ``BHAPI_IDENTITY_PARTNER`` env var once a partner agreement is
signed.

Cross-product data sharing requires explicit per-user consent (separate from
the Family+ subscription consent). See ``IdentityProtectionLink`` model and
``activate_identity_protection`` flow.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import IdentityProtectionLink
from src.exceptions import ConflictError, ValidationError

logger = structlog.get_logger()


CURRENT_CONSENT_TEXT_VERSION = "v1"


@dataclass
class PartnerProvisionResult:
    """Result returned by a partner client after successful provisioning."""

    partner_account_id: str
    metadata: dict


class PartnerClient(ABC):
    """Abstract base — every identity-protection partner implements this."""

    name: str = "abstract"

    @abstractmethod
    async def create_account(
        self, user_id: uuid.UUID, email: str, dependents: list[dict] | None = None
    ) -> PartnerProvisionResult:
        """Provision a new account at the partner. Idempotent on user_id."""

    @abstractmethod
    async def cancel_account(self, partner_account_id: str) -> None:
        """Cancel an existing partner account."""


class MockPartnerClient(PartnerClient):
    """In-memory mock partner — used when no real partner is configured.

    Does NOT call any external service; logs every call. Safe for tests and
    pre-launch local development.
    """

    name = "mock"

    async def create_account(
        self, user_id: uuid.UUID, email: str, dependents: list[dict] | None = None
    ) -> PartnerProvisionResult:
        partner_account_id = f"mock-{uuid.uuid4().hex[:12]}"
        logger.info(
            "identity_partner.mock.create_account",
            partner=self.name,
            user_id=str(user_id),
            partner_account_id=partner_account_id,
            dependents_count=len(dependents or []),
        )
        return PartnerProvisionResult(
            partner_account_id=partner_account_id,
            metadata={"mock": True, "dependents": len(dependents or [])},
        )

    async def cancel_account(self, partner_account_id: str) -> None:
        logger.info(
            "identity_partner.mock.cancel_account",
            partner=self.name,
            partner_account_id=partner_account_id,
        )


_PARTNER_CLIENT: PartnerClient | None = None


def get_partner_client() -> PartnerClient:
    """Return the configured partner client (singleton).

    Selection by ``BHAPI_IDENTITY_PARTNER`` env var. Defaults to ``MockPartnerClient``
    until a real partnership is signed.
    """
    global _PARTNER_CLIENT
    if _PARTNER_CLIENT is not None:
        return _PARTNER_CLIENT

    partner_name = os.getenv("BHAPI_IDENTITY_PARTNER", "mock").lower()
    if partner_name == "mock":
        _PARTNER_CLIENT = MockPartnerClient()
    else:
        # Real partner clients are added here once contracts are signed.
        logger.warning(
            "identity_partner.unknown_partner_falling_back_to_mock",
            requested=partner_name,
        )
        _PARTNER_CLIENT = MockPartnerClient()
    return _PARTNER_CLIENT


def reset_partner_client() -> None:
    """Reset the singleton — for tests."""
    global _PARTNER_CLIENT
    _PARTNER_CLIENT = None


async def activate_identity_protection(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str,
    consent_text_version: str,
    agreed: bool,
    dependents: list[dict] | None = None,
) -> IdentityProtectionLink:
    """Create a partner account + persist the consent record.

    Raises ``ValidationError`` if the user did not agree, or if the consent
    version differs from the current canonical version. Raises ``ConflictError``
    if an active link already exists for the user (idempotency boundary).
    """
    if not agreed:
        raise ValidationError(
            "Activation requires explicit consent — cannot enable identity "
            "protection without agreed=True."
        )
    if consent_text_version != CURRENT_CONSENT_TEXT_VERSION:
        raise ValidationError(
            f"Consent text version mismatch — expected "
            f"{CURRENT_CONSENT_TEXT_VERSION!r}, got {consent_text_version!r}. "
            "Reload the consent screen and accept the current version."
        )

    existing = (
        await db.execute(
            select(IdentityProtectionLink).where(
                IdentityProtectionLink.user_id == user_id,
                IdentityProtectionLink.status == "active",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "Identity protection is already active for this user."
        )

    client = get_partner_client()
    result = await client.create_account(user_id=user_id, email=email, dependents=dependents)

    link = IdentityProtectionLink(
        user_id=user_id,
        partner_name=client.name,
        partner_account_id=result.partner_account_id,
        consent_given_at=datetime.now(timezone.utc),
        consent_text_version=consent_text_version,
        status="active",
        metadata_json=result.metadata,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    logger.info(
        "identity_partner.activated",
        user_id=str(user_id),
        partner=client.name,
        partner_account_id=result.partner_account_id,
    )
    return link


async def revoke_identity_protection(
    db: AsyncSession, *, user_id: uuid.UUID
) -> bool:
    """Cancel the active partner link for the user. Returns True if a link
    was found and revoked, False if no active link existed.
    """
    link = (
        await db.execute(
            select(IdentityProtectionLink).where(
                IdentityProtectionLink.user_id == user_id,
                IdentityProtectionLink.status == "active",
            )
        )
    ).scalar_one_or_none()
    if link is None:
        return False

    client = get_partner_client()
    await client.cancel_account(link.partner_account_id)

    link.status = "cancelled"
    await db.commit()
    logger.info(
        "identity_partner.revoked",
        user_id=str(user_id),
        partner=link.partner_name,
        partner_account_id=link.partner_account_id,
    )
    return True


async def get_identity_protection_status(
    db: AsyncSession, *, user_id: uuid.UUID
) -> IdentityProtectionLink | None:
    """Return the most recent IdentityProtectionLink for a user, if any."""
    return (
        await db.execute(
            select(IdentityProtectionLink)
            .where(IdentityProtectionLink.user_id == user_id)
            .order_by(IdentityProtectionLink.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
