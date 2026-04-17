"""Age-tier enforcement middleware — checks age-tier permissions on social endpoints.

This is a FastAPI dependency (not ASGI middleware) that:
1. Resolves the user's age tier from their social profile
2. Maps the current endpoint to a required permission
3. Checks the tier's permission matrix
4. Raises ForbiddenError if the permission is denied

Adults/parents without a social profile are not subject to restrictions.
"""

import re
from typing import Any

import structlog
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import AgeTier, check_permission
from src.auth import get_current_user
from src.database import get_db
from src.exceptions import ForbiddenError
from src.schemas import GroupContext

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Endpoint → permission mapping
# ---------------------------------------------------------------------------

# Static routes (exact match on method + path)
STATIC_ENDPOINT_PERMISSIONS: dict[tuple[str, str], str] = {
    # Social — posts
    ("POST", "/api/v1/social/posts"): "can_post",
    ("GET", "/api/v1/social/posts"): "can_post",
    ("GET", "/api/v1/social/posts/{post_id}"): "can_post",
    ("DELETE", "/api/v1/social/posts/{post_id}"): "can_post",
    # Social — feed
    ("GET", "/api/v1/social/feed"): "can_post",
    # Social — likes
    ("POST", "/api/v1/social/posts/{post_id}/like"): "can_like",
    ("DELETE", "/api/v1/social/posts/{post_id}/like"): "can_like",
    # Social — comments
    ("POST", "/api/v1/social/posts/{post_id}/comments"): "can_comment",
    ("GET", "/api/v1/social/posts/{post_id}/comments"): "can_comment",
    # Social — follows
    ("POST", "/api/v1/social/follow/{user_id}"): "can_follow",
    ("DELETE", "/api/v1/social/follow/{user_id}"): "can_follow",
    ("PATCH", "/api/v1/social/follow/{follow_id}/accept"): "can_follow",
    ("GET", "/api/v1/social/followers"): "can_follow",
    ("GET", "/api/v1/social/following"): "can_follow",
    # Social — search
    ("GET", "/api/v1/social/search"): "can_search_users",
    # Social — hashtags
    ("GET", "/api/v1/social/hashtags/trending"): "can_post",
    # Contacts
    ("POST", "/api/v1/contacts/request/{user_id}"): "can_add_contacts",
    ("PATCH", "/api/v1/contacts/{id}/respond"): "can_add_contacts",
    ("PATCH", "/api/v1/contacts/{id}/parent-approve"): "can_add_contacts",
    ("POST", "/api/v1/contacts/{user_id}/block"): "can_add_contacts",
    ("GET", "/api/v1/contacts"): "can_add_contacts",
    ("GET", "/api/v1/contacts/pending"): "can_add_contacts",
    # Messaging — conversations
    ("POST", "/api/v1/messages/conversations"): "can_message",
    ("GET", "/api/v1/messages/conversations"): "can_message",
    ("GET", "/api/v1/messages/conversations/{conversation_id}"): "can_message",
    # Messaging — messages
    ("POST", "/api/v1/messages/conversations/{conversation_id}/messages"): "can_message",
    ("GET", "/api/v1/messages/conversations/{conversation_id}/messages"): "can_message",
    ("PATCH", "/api/v1/messages/conversations/{conversation_id}/read"): "can_message",
    # Media — upload (image)
    ("POST", "/api/v1/media/upload"): "can_upload_image",
    ("POST", "/api/v1/media/register"): "can_upload_image",
    ("GET", "/api/v1/media"): "can_upload_image",
    ("GET", "/api/v1/media/{media_id}"): "can_upload_image",
    ("GET", "/api/v1/media/{media_id}/variants"): "can_upload_image",
    ("DELETE", "/api/v1/media/{media_id}"): "can_upload_image",
}

# Compile regex patterns from the static routes for runtime matching.
# The {param} placeholders become regex groups.
_PATTERN_CACHE: list[tuple[str, re.Pattern[str], str]] = []

_UUID_REGEX = r"[0-9a-fA-F-]+"

for (method, template), permission in STATIC_ENDPOINT_PERMISSIONS.items():
    # Convert /api/v1/social/posts/{post_id}/comments to regex
    regex_str = re.sub(r"\{[^}]+\}", _UUID_REGEX, template)
    # Anchor and make exact
    pattern = re.compile(f"^{regex_str}$")
    _PATTERN_CACHE.append((method, pattern, permission))


def _match_endpoint(method: str, path: str) -> str | None:
    """Match an HTTP method + path to a permission name.

    Returns the permission string or None if no match (endpoint not protected).
    """
    # Strip trailing slash for consistency (but keep root slash)
    normalized = path.rstrip("/") if path != "/" else path

    for route_method, pattern, permission in _PATTERN_CACHE:
        if method == route_method and pattern.match(normalized):
            return permission
    return None


async def _get_user_age_tier(db: AsyncSession, user_id: Any) -> AgeTier | None:
    """Get the user's age tier from their social profile.

    Returns None if the user has no social profile (adults/parents).
    """
    try:
        from src.social.service import get_profile

        profile = await get_profile(db, user_id)
        return AgeTier(profile.age_tier)
    except Exception as exc:
        logger.debug(
            "age_tier_middleware_profile_lookup_degraded",
            error=str(exc),
            user_id=str(user_id),
        )
        return None


async def enforce_age_tier(
    request: Request,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """FastAPI dependency that enforces age-tier permissions on social endpoints.

    - Matches the current request to an age-tier permission
    - If no match, allows the request (endpoint not subject to age-tier restrictions)
    - If the user has no social profile, allows the request (adult/parent)
    - Otherwise, checks the tier permission and raises ForbiddenError if denied
    """
    method = request.method
    path = request.url.path

    # 1. Find the required permission for this endpoint
    required_permission = _match_endpoint(method, path)
    if required_permission is None:
        # Endpoint not in the protection map — allow
        return

    # 2. Get the user's age tier
    tier = await _get_user_age_tier(db, auth.user_id)
    if tier is None:
        # No social profile — user is likely an adult/parent, allow
        return

    # 3. Check permission
    allowed = check_permission(tier, required_permission)
    if not allowed:
        logger.warning(
            "age_tier_permission_denied",
            user_id=str(auth.user_id),
            tier=tier.value,
            permission=required_permission,
            method=method,
            path=path,
        )
        raise ForbiddenError(
            f"Your age tier ({tier.value}) does not have permission "
            f"for this action ({required_permission})"
        )

    logger.debug(
        "age_tier_permission_granted",
        user_id=str(auth.user_id),
        tier=tier.value,
        permission=required_permission,
    )
