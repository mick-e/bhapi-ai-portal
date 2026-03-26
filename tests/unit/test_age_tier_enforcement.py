"""Unit tests for age-tier enforcement middleware.

Tests the middleware dependency that checks age-tier permissions
on social, contacts, messaging, and media endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.age_tier.middleware import (
    STATIC_ENDPOINT_PERMISSIONS,
    _match_endpoint,
    enforce_age_tier,
)
from src.age_tier.rules import TIER_PERMISSIONS, AgeTier
from src.exceptions import ForbiddenError
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# _match_endpoint unit tests
# ---------------------------------------------------------------------------


class TestMatchEndpoint:
    """Test the endpoint→permission matching logic."""

    def test_post_create_post(self):
        """POST /api/v1/social/posts maps to can_post."""
        assert _match_endpoint("POST", "/api/v1/social/posts") == "can_post"

    def test_post_comment(self):
        """POST /api/v1/social/posts/{id}/comments maps to can_comment."""
        perm = _match_endpoint(
            "POST", "/api/v1/social/posts/550e8400-e29b-41d4-a716-446655440000/comments"
        )
        assert perm == "can_comment"

    def test_post_like(self):
        """POST /api/v1/social/posts/{id}/like maps to can_like."""
        perm = _match_endpoint(
            "POST", "/api/v1/social/posts/550e8400-e29b-41d4-a716-446655440000/like"
        )
        assert perm == "can_like"

    def test_get_search(self):
        """GET /api/v1/social/search maps to can_search_users."""
        assert _match_endpoint("GET", "/api/v1/social/search") == "can_search_users"

    def test_post_contact_request(self):
        """POST /api/v1/contacts/request/{id} maps to can_add_contacts."""
        perm = _match_endpoint(
            "POST", "/api/v1/contacts/request/550e8400-e29b-41d4-a716-446655440000"
        )
        assert perm == "can_add_contacts"

    def test_post_conversation(self):
        """POST /api/v1/messages/conversations maps to can_message."""
        assert _match_endpoint("POST", "/api/v1/messages/conversations") == "can_message"

    def test_post_message_in_conversation(self):
        """POST /api/v1/messages/conversations/{id}/messages maps to can_message."""
        perm = _match_endpoint(
            "POST",
            "/api/v1/messages/conversations/550e8400-e29b-41d4-a716-446655440000/messages",
        )
        assert perm == "can_message"

    def test_post_media_upload(self):
        """POST /api/v1/media/upload maps to can_upload_image."""
        assert _match_endpoint("POST", "/api/v1/media/upload") == "can_upload_image"

    def test_follow_user(self):
        """POST /api/v1/social/follow/{id} maps to can_follow."""
        perm = _match_endpoint(
            "POST", "/api/v1/social/follow/550e8400-e29b-41d4-a716-446655440000"
        )
        assert perm == "can_follow"

    def test_unmatched_endpoint_returns_none(self):
        """Endpoint not in the map returns None."""
        assert _match_endpoint("GET", "/api/v1/auth/me") is None

    def test_wrong_method_returns_none(self):
        """Correct path but wrong method returns None."""
        assert _match_endpoint("PUT", "/api/v1/social/posts") is None

    def test_trailing_slash_stripped(self):
        """Trailing slash is normalized."""
        assert _match_endpoint("POST", "/api/v1/social/posts/") == "can_post"

    def test_get_feed(self):
        """GET /api/v1/social/feed maps to can_post."""
        assert _match_endpoint("GET", "/api/v1/social/feed") == "can_post"

    def test_get_trending_hashtags(self):
        """GET /api/v1/social/hashtags/trending maps to can_post."""
        assert _match_endpoint("GET", "/api/v1/social/hashtags/trending") == "can_post"

    def test_get_contacts_list(self):
        """GET /api/v1/contacts maps to can_add_contacts."""
        assert _match_endpoint("GET", "/api/v1/contacts") == "can_add_contacts"

    def test_get_contacts_list_trailing_slash(self):
        """GET /api/v1/contacts/ also matches (trailing slash normalized)."""
        assert _match_endpoint("GET", "/api/v1/contacts/") == "can_add_contacts"

    def test_get_pending_contacts(self):
        """GET /api/v1/contacts/pending maps to can_add_contacts."""
        assert _match_endpoint("GET", "/api/v1/contacts/pending") == "can_add_contacts"

    def test_mark_read(self):
        """PATCH /api/v1/messages/conversations/{id}/read maps to can_message."""
        perm = _match_endpoint(
            "PATCH",
            "/api/v1/messages/conversations/550e8400-e29b-41d4-a716-446655440000/read",
        )
        assert perm == "can_message"

    def test_delete_media(self):
        """DELETE /api/v1/media/{id} maps to can_upload_image."""
        perm = _match_endpoint(
            "DELETE", "/api/v1/media/550e8400-e29b-41d4-a716-446655440000"
        )
        assert perm == "can_upload_image"


# ---------------------------------------------------------------------------
# Permission matrix verification
# ---------------------------------------------------------------------------


class TestPermissionMatrix:
    """Verify the permission matrix matches expectations per ADR-009."""

    def test_young_cannot_message(self):
        """Young tier (5-9) cannot message."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_message"] is False

    def test_young_cannot_search(self):
        """Young tier (5-9) cannot search users."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_search_users"] is False

    def test_young_cannot_add_contacts(self):
        """Young tier (5-9) cannot add contacts."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_add_contacts"] is False

    def test_young_cannot_upload_video(self):
        """Young tier (5-9) cannot upload video."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_upload_video"] is False

    def test_young_can_post(self):
        """Young tier (5-9) can post."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_post"] is True

    def test_young_can_like(self):
        """Young tier (5-9) can like."""
        assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_like"] is True

    def test_preteen_can_message(self):
        """Preteen tier (10-12) can message."""
        assert TIER_PERMISSIONS[AgeTier.PRETEEN]["can_message"] is True

    def test_preteen_can_search(self):
        """Preteen tier (10-12) can search users."""
        assert TIER_PERMISSIONS[AgeTier.PRETEEN]["can_search_users"] is True

    def test_preteen_cannot_upload_video(self):
        """Preteen tier (10-12) cannot upload video."""
        assert TIER_PERMISSIONS[AgeTier.PRETEEN]["can_upload_video"] is False

    def test_teen_can_upload_video(self):
        """Teen tier (13-15) can upload video."""
        assert TIER_PERMISSIONS[AgeTier.TEEN]["can_upload_video"] is True

    def test_teen_can_message(self):
        """Teen tier (13-15) can message."""
        assert TIER_PERMISSIONS[AgeTier.TEEN]["can_message"] is True

    def test_teen_can_create_group_chat(self):
        """Teen tier (13-15) can create group chat."""
        assert TIER_PERMISSIONS[AgeTier.TEEN]["can_create_group_chat"] is True


# ---------------------------------------------------------------------------
# enforce_age_tier dependency tests
# ---------------------------------------------------------------------------


class TestEnforceAgeTier:
    """Test the enforce_age_tier FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_unprotected_endpoint_passes(self):
        """Requests to unprotected endpoints pass through."""
        request = AsyncMock()
        request.method = "GET"
        request.url.path = "/api/v1/auth/me"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        # Should not raise
        await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_adult_without_profile_passes(self):
        """Adults without a social profile are not restricted."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/social/posts"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        # Mock get_profile to raise (no profile)
        with patch("src.age_tier.middleware._get_user_age_tier", return_value=None):
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_young_denied_messaging(self):
        """Young tier denied access to messaging endpoints."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/messages/conversations"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            with pytest.raises(ForbiddenError) as exc_info:
                await enforce_age_tier(request, auth, db)
            assert "can_message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_young_denied_search(self):
        """Young tier denied access to search endpoint."""
        request = AsyncMock()
        request.method = "GET"
        request.url.path = "/api/v1/social/search"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            with pytest.raises(ForbiddenError) as exc_info:
                await enforce_age_tier(request, auth, db)
            assert "can_search_users" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_young_denied_contacts(self):
        """Young tier denied access to contact request."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/contacts/request/550e8400-e29b-41d4-a716-446655440000"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            with pytest.raises(ForbiddenError) as exc_info:
                await enforce_age_tier(request, auth, db)
            assert "can_add_contacts" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preteen_allowed_messaging(self):
        """Preteen tier allowed to access messaging endpoints."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/messages/conversations"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.PRETEEN,
        ):
            # Should not raise
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_preteen_allowed_search(self):
        """Preteen tier allowed to search users."""
        request = AsyncMock()
        request.method = "GET"
        request.url.path = "/api/v1/social/search"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.PRETEEN,
        ):
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_teen_allowed_messaging(self):
        """Teen tier allowed to access messaging."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/messages/conversations"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.TEEN,
        ):
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_young_allowed_posting(self):
        """Young tier allowed to post (can_post is True)."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/social/posts"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_young_allowed_liking(self):
        """Young tier allowed to like posts."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/social/posts/550e8400-e29b-41d4-a716-446655440000/like"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            await enforce_age_tier(request, auth, db)

    @pytest.mark.asyncio
    async def test_forbidden_includes_tier_name(self):
        """ForbiddenError message includes the tier name."""
        request = AsyncMock()
        request.method = "POST"
        request.url.path = "/api/v1/messages/conversations"
        auth = GroupContext(user_id="00000000-0000-0000-0000-000000000001")
        db = AsyncMock()

        with patch(
            "src.age_tier.middleware._get_user_age_tier",
            return_value=AgeTier.YOUNG,
        ):
            with pytest.raises(ForbiddenError) as exc_info:
                await enforce_age_tier(request, auth, db)
            assert "young" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Endpoint coverage — verify all protected routes are in the map
# ---------------------------------------------------------------------------


class TestEndpointCoverage:
    """Verify the endpoint permission map has complete coverage."""

    def test_all_social_write_endpoints_covered(self):
        """All social write endpoints are in the permission map."""
        social_write_endpoints = [
            ("POST", "/api/v1/social/posts"),
            ("POST", "/api/v1/social/posts/{post_id}/like"),
            ("POST", "/api/v1/social/posts/{post_id}/comments"),
            ("POST", "/api/v1/social/follow/{user_id}"),
            ("DELETE", "/api/v1/social/posts/{post_id}"),
            ("DELETE", "/api/v1/social/posts/{post_id}/like"),
            ("DELETE", "/api/v1/social/follow/{user_id}"),
        ]
        for method, path in social_write_endpoints:
            assert (method, path) in STATIC_ENDPOINT_PERMISSIONS, \
                f"Missing: {method} {path}"

    def test_all_contacts_endpoints_covered(self):
        """All contacts endpoints are in the permission map."""
        contacts_endpoints = [
            ("POST", "/api/v1/contacts/request/{user_id}"),
            ("PATCH", "/api/v1/contacts/{id}/respond"),
            ("PATCH", "/api/v1/contacts/{id}/parent-approve"),
            ("POST", "/api/v1/contacts/{user_id}/block"),
            ("GET", "/api/v1/contacts"),
            ("GET", "/api/v1/contacts/pending"),
        ]
        for method, path in contacts_endpoints:
            assert (method, path) in STATIC_ENDPOINT_PERMISSIONS, \
                f"Missing: {method} {path}"

    def test_all_messaging_endpoints_covered(self):
        """All messaging endpoints are in the permission map."""
        messaging_endpoints = [
            ("POST", "/api/v1/messages/conversations"),
            ("GET", "/api/v1/messages/conversations"),
            ("GET", "/api/v1/messages/conversations/{conversation_id}"),
            ("POST", "/api/v1/messages/conversations/{conversation_id}/messages"),
            ("GET", "/api/v1/messages/conversations/{conversation_id}/messages"),
            ("PATCH", "/api/v1/messages/conversations/{conversation_id}/read"),
        ]
        for method, path in messaging_endpoints:
            assert (method, path) in STATIC_ENDPOINT_PERMISSIONS, \
                f"Missing: {method} {path}"

    def test_all_media_endpoints_covered(self):
        """All media endpoints are in the permission map."""
        media_endpoints = [
            ("POST", "/api/v1/media/upload"),
            ("POST", "/api/v1/media/register"),
            ("GET", "/api/v1/media"),
            ("GET", "/api/v1/media/{media_id}"),
            ("GET", "/api/v1/media/{media_id}/variants"),
            ("DELETE", "/api/v1/media/{media_id}"),
        ]
        for method, path in media_endpoints:
            assert (method, path) in STATIC_ENDPOINT_PERMISSIONS, \
                f"Missing: {method} {path}"
