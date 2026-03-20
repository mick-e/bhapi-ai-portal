"""JWT validation for WebSocket connections."""

import structlog

from src.auth.service import decode_token

logger = structlog.get_logger()


async def validate_ws_token(token: str) -> dict | None:
    """Validate JWT token for WebSocket connection.

    Returns payload dict with user_id, group_id, role, permissions.
    Returns None for invalid tokens (WebSocket close, not HTTP error).
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "session":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return {
            "user_id": user_id,
            "group_id": payload.get("group_id"),
            "role": payload.get("role", "member"),
            "permissions": payload.get("permissions", []),
        }
    except Exception:
        logger.warning("ws_token_invalid")
        return None
