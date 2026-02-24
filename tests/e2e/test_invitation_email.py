"""End-to-end tests for group invitation email feature.

Verifies that create_invitation in src.groups.service creates an invitation
with proper fields and triggers the email service (logged in test mode).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.groups.models import Group, GroupMember, Invitation
from src.groups.schemas import InvitationCreate
from src.groups.service import create_invitation


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession) -> User:
    """Create a test user in the users table."""
    user = User(
        id=uuid.uuid4(),
        email=f"inviter-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def test_group(test_session: AsyncSession, test_user: User) -> Group:
    """Create a group owned by the test user."""
    group = Group(
        id=uuid.uuid4(),
        name="Smith Family",
        type="family",
        owner_id=test_user.id,
        settings={},
    )
    test_session.add(group)
    await test_session.flush()
    return group


@pytest_asyncio.fixture
async def test_member(
    test_session: AsyncSession, test_group: Group, test_user: User
) -> GroupMember:
    """Create a GroupMember record with parent role for the test user."""
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=test_group.id,
        user_id=test_user.id,
        role="parent",
        display_name="Test Parent",
    )
    test_session.add(member)
    await test_session.flush()
    return member


class TestInvitationEmailCreation:
    """Test that create_invitation creates a proper invitation and triggers email."""

    @pytest.mark.asyncio
    async def test_create_invitation_success(
        self, test_session, test_user, test_group, test_member
    ):
        """Invitation is created successfully with correct fields."""
        data = InvitationCreate(email="invited@example.com", role="member")

        invitation = await create_invitation(
            test_session, test_group.id, test_user.id, data
        )

        assert invitation is not None
        assert isinstance(invitation, Invitation)
        assert invitation.id is not None

    @pytest.mark.asyncio
    async def test_send_email_called(
        self, test_session, test_user, test_group, test_member
    ):
        """The email service send_email function is called during invitation creation."""
        data = InvitationCreate(email="emailcheck@example.com", role="member")

        with patch(
            "src.email.service.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            invitation = await create_invitation(
                test_session, test_group.id, test_user.id, data
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args
            assert call_kwargs.kwargs["to_email"] == "emailcheck@example.com"
            assert call_kwargs.kwargs["group_id"] == str(test_group.id)
            assert invitation is not None

    @pytest.mark.asyncio
    async def test_invitation_token_in_url(
        self, test_session, test_user, test_group, test_member
    ):
        """The invitation token is present in the invitation_url passed to send_email."""
        data = InvitationCreate(email="tokencheck@example.com", role="member")

        with patch(
            "src.email.service.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            invitation = await create_invitation(
                test_session, test_group.id, test_user.id, data
            )

            # The template is called with invitation_url containing the token
            # We verify the token exists and is non-empty
            assert invitation.token is not None
            assert len(invitation.token) > 0

            # Verify the invitation_url passed to the template contains the token
            # The service builds: f"https://bhapi.ai/invite/{token}"
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "html_content" in call_kwargs
            assert invitation.token in call_kwargs["html_content"]

    @pytest.mark.asyncio
    async def test_invitation_has_proper_fields(
        self, test_session, test_user, test_group, test_member
    ):
        """The invitation has proper email, role, status, and expires_at fields."""
        data = InvitationCreate(email="fields@example.com", role="member")

        invitation = await create_invitation(
            test_session, test_group.id, test_user.id, data
        )

        # email
        assert invitation.email == "fields@example.com"

        # role
        assert invitation.role == "member"

        # status
        assert invitation.status == "pending"

        # expires_at is set and in the future
        assert invitation.expires_at is not None
        now = datetime.now(timezone.utc)
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > now

        # Additional fields set by create_invitation
        assert invitation.group_id == test_group.id
        assert invitation.invited_by == test_user.id
        assert invitation.token is not None
        assert invitation.consent_required is False

    @pytest.mark.asyncio
    async def test_email_failure_does_not_break_invitation(
        self, test_session, test_user, test_group, test_member
    ):
        """If send_email raises, the invitation is still created (error is caught)."""
        data = InvitationCreate(email="failmail@example.com", role="member")

        with patch(
            "src.email.service.send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.side_effect = Exception("SMTP connection failed")

            invitation = await create_invitation(
                test_session, test_group.id, test_user.id, data
            )

            # Invitation still created despite email failure
            assert invitation is not None
            assert invitation.email == "failmail@example.com"
            assert invitation.status == "pending"

    @pytest.mark.asyncio
    async def test_invitation_email_in_dev_mode_logs(
        self, test_session, test_user, test_group, test_member
    ):
        """In test environment, send_email logs instead of sending (returns True)."""
        data = InvitationCreate(email="devmode@example.com", role="member")

        # Do not mock send_email -- let it run with ENVIRONMENT=test
        # The conftest sets ENVIRONMENT=test, so send_email logs and returns True
        invitation = await create_invitation(
            test_session, test_group.id, test_user.id, data
        )

        assert invitation is not None
        assert invitation.email == "devmode@example.com"
        assert invitation.status == "pending"
        assert invitation.token is not None
