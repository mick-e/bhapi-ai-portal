"""API platform webhook delivery — HMAC-signed POST to registered endpoints."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.models import PlatformWebhookDelivery, PlatformWebhookEndpoint

logger = structlog.get_logger()

WEBHOOK_EVENTS = [
    "alert.created",
    "risk_score.changed",
    "compliance.report_ready",
    "checkin.event",
    "screen_time.limit_reached",
]

# Retry delays in seconds: 10s, 60s, 300s
RETRY_DELAYS = [10, 60, 300]


def sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.

    Follows the Stripe webhook pattern — returns the hex digest.
    The signature covers the raw payload string.
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: str, secret: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature using constant-time comparison.

    Returns True if the signature matches, False otherwise.
    """
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


async def deliver_webhook(
    db: AsyncSession,
    endpoint: PlatformWebhookEndpoint,
    event_type: str,
    payload: dict,
) -> PlatformWebhookDelivery:
    """Deliver a webhook to a registered endpoint with HMAC-SHA256 signature.

    Creates a PlatformWebhookDelivery record, then attempts delivery up to
    len(RETRY_DELAYS) + 1 times.  Each attempt updates the delivery record.

    In production the retry delays would be handled by a background job queue.
    For now, only the first attempt executes; retries are logged as warnings.
    """
    payload_str = json.dumps(payload, default=str)
    # secret_hash stores the hashed secret — for signing we use it as-is.
    # In production with KMS the plaintext secret would be decrypted first.
    signature = sign_payload(payload_str, endpoint.secret_hash)
    timestamp = datetime.now(timezone.utc).isoformat()

    headers = {
        "Content-Type": "application/json",
        "X-Bhapi-Signature": f"sha256={signature}",
        "X-Bhapi-Event": event_type,
        "X-Bhapi-Timestamp": timestamp,
    }

    delivery = PlatformWebhookDelivery(
        id=uuid4(),
        endpoint_id=endpoint.id,
        event_type=event_type,
        payload=payload,
        attempt_count=0,
        delivered=False,
    )
    db.add(delivery)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(len(RETRY_DELAYS) + 1):
            delivery.attempt_count = attempt + 1
            try:
                response = await client.post(
                    endpoint.url, content=payload_str, headers=headers,
                )
                delivery.status_code = response.status_code
                # httpx sets elapsed after the response is received
                try:
                    delivery.response_time_ms = int(
                        response.elapsed.total_seconds() * 1000
                    )
                except Exception:
                    delivery.response_time_ms = None

                if 200 <= response.status_code < 300:
                    delivery.delivered = True
                    logger.info(
                        "webhook_delivered",
                        endpoint_id=str(endpoint.id),
                        event_type=event_type,
                        status_code=response.status_code,
                        attempt=attempt + 1,
                    )
                    break

                logger.warning(
                    "webhook_delivery_failed",
                    endpoint_id=str(endpoint.id),
                    event_type=event_type,
                    status_code=response.status_code,
                    attempt=attempt + 1,
                )

            except Exception as exc:
                delivery.error = str(exc)
                logger.warning(
                    "webhook_delivery_error",
                    endpoint_id=str(endpoint.id),
                    event_type=event_type,
                    error=str(exc),
                    attempt=attempt + 1,
                )

            if attempt < len(RETRY_DELAYS):
                # In production, schedule retry via background job scheduler.
                # Log the retry delay that would be applied.
                logger.warning(
                    "webhook_retry_scheduled",
                    endpoint_id=str(endpoint.id),
                    attempt=attempt + 1,
                    delay_seconds=RETRY_DELAYS[attempt],
                )
                # Do not actually sleep in the synchronous path —
                # break after first attempt and let the caller retry.
                break

    await db.flush()
    return delivery


async def deliver_event_to_subscribers(
    db: AsyncSession,
    event_type: str,
    payload: dict,
) -> list[PlatformWebhookDelivery]:
    """Find all active endpoints subscribed to this event and deliver.

    An endpoint is a subscriber if its events list contains the exact event_type
    or the wildcard "*".

    Returns a list of PlatformWebhookDelivery records (one per endpoint).
    """
    result = await db.execute(
        select(PlatformWebhookEndpoint).where(
            PlatformWebhookEndpoint.is_active == True,  # noqa: E712
        )
    )
    endpoints = result.scalars().all()

    deliveries: list[PlatformWebhookDelivery] = []
    for endpoint in endpoints:
        events: list = endpoint.events or []
        if event_type in events or "*" in events:
            delivery = await deliver_webhook(db, endpoint, event_type, payload)
            deliveries.append(delivery)

    return deliveries
