"""Yoti Age Check API integration."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.exceptions import NotFoundError

logger = structlog.get_logger()


async def create_age_verification_session(member_id: str) -> dict:
    """Create a Yoti age verification session. Returns session URL."""
    settings = get_settings()

    if settings.environment in ("development", "test"):
        logger.info("yoti_session_dev_mode", member_id=member_id)
        return {"session_id": f"dev_session_{member_id}", "url": f"https://yoti.com/verify/dev_{member_id}"}

    sdk_id = settings.yoti_client_sdk_id
    if not sdk_id:
        raise ValueError("YOTI_CLIENT_SDK_ID not configured")

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.yoti.com/idverify/v1/sessions",
            headers={"X-Yoti-Auth-Id": sdk_id},
            json={
                "session_deadline": "2099-01-01T00:00:00Z",
                "resources_ttl": 604800,
                "requested_checks": [{"type": "ID_DOCUMENT_AUTHENTICITY"}, {"type": "LIVENESS"}],
                "requested_tasks": [{"type": "ID_DOCUMENT_TEXT_DATA_EXTRACTION"}],
            },
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {"session_id": data.get("session_id", ""), "url": data.get("client_session_token_ttl", "")}
        logger.error("yoti_session_error", status=resp.status_code)
        raise ValueError(f"Yoti session creation failed: {resp.status_code}")


async def get_age_verification_result(session_id: str) -> dict:
    """Get the result of a Yoti age verification session."""
    settings = get_settings()

    if settings.environment in ("development", "test"):
        return {"verified": True, "age": 12, "session_id": session_id}

    sdk_id = settings.yoti_client_sdk_id
    if not sdk_id:
        raise ValueError("YOTI_CLIENT_SDK_ID not configured")

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"https://api.yoti.com/idverify/v1/sessions/{session_id}",
            headers={"X-Yoti-Auth-Id": sdk_id},
        )
        if resp.status_code == 200:
            data = resp.json()
            checks = data.get("checks", [])
            age = None
            for check in checks:
                report = check.get("report", {})
                breakdown = report.get("breakdown", [])
                for item in breakdown:
                    if "age" in item.get("sub_check", "").lower():
                        age = item.get("result", {}).get("value")
            return {
                "verified": data.get("state") == "COMPLETED",
                "age": int(age) if age else None,
                "session_id": session_id,
            }
        raise ValueError(f"Yoti result fetch failed: {resp.status_code}")


async def handle_yoti_callback(
    db: AsyncSession, session_id: str, status: str, score: float | None = None
) -> dict:
    """Process Yoti verification callback.

    Updates the VideoVerification record matching the yoti_session_id.
    """
    from src.compliance.coppa_2026 import complete_video_verification
    from src.compliance.models import VideoVerification

    result = await db.execute(
        select(VideoVerification).where(
            VideoVerification.yoti_session_id == session_id
        )
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise NotFoundError("VideoVerification with yoti_session_id", session_id)

    if status == "DONE":
        await complete_video_verification(db, verification.id, score or 0.9)
    elif status == "FAILED":
        await complete_video_verification(db, verification.id, 0.0)

    logger.info(
        "yoti_callback_processed",
        session_id=session_id,
        status=status,
        verification_id=str(verification.id),
    )
    return {"verification_id": str(verification.id), "status": verification.status}
