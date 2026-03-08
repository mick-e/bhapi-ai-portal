"""E2E tests for Clever and ClassLink SIS integrations."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.encryption import encrypt_credential, decrypt_credential
from src.groups.models import GroupMember
from src.integrations.models import SISConnection
from src.integrations.sis_sync import sync_roster
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_sync_roster_creates_members(test_session):
    """Roster sync should create new GroupMembers from SIS data."""
    group, owner_id = await make_test_group(test_session, name="School", group_type="school")

    roster = [
        {"first_name": "Alice", "last_name": "Smith", "email": "alice@school.com", "role": "member"},
        {"first_name": "Bob", "last_name": "Jones", "email": "bob@school.com", "role": "member"},
    ]

    result = await sync_roster(test_session, group.id, roster)
    assert result["members_created"] == 2
    assert result["members_updated"] == 0

    from sqlalchemy import select
    members = await test_session.execute(
        select(GroupMember).where(GroupMember.group_id == group.id)
    )
    names = [m.display_name for m in members.scalars().all()]
    assert "Alice Smith" in names
    assert "Bob Jones" in names


@pytest.mark.asyncio
async def test_sync_roster_updates_existing(test_session):
    """Roster sync should count existing members as updated."""
    group, owner_id = await make_test_group(test_session, name="School", group_type="school")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Alice Smith",
    )
    test_session.add(member)
    await test_session.flush()

    roster = [
        {"first_name": "Alice", "last_name": "Smith", "email": "alice@school.com", "role": "member"},
        {"first_name": "Charlie", "last_name": "Brown", "email": "charlie@school.com", "role": "member"},
    ]

    result = await sync_roster(test_session, group.id, roster)
    assert result["members_created"] == 1
    assert result["members_updated"] == 1


@pytest.mark.asyncio
async def test_sis_connection_credential_encryption(test_session):
    """SIS connection credentials should be encrypted at rest."""
    group, owner_id = await make_test_group(test_session, name="School", group_type="school")

    token = "clever_token_abc123"
    conn = SISConnection(
        id=uuid4(), group_id=group.id, provider="clever",
        credentials_encrypted=encrypt_credential(token),
        status="active",
    )
    test_session.add(conn)
    await test_session.flush()

    # Raw stored value is not the plaintext
    assert conn.credentials_encrypted != token
    assert conn.credentials_encrypted.startswith("fernet:")

    # Can decrypt back
    assert decrypt_credential(conn.credentials_encrypted) == token


@pytest.mark.asyncio
async def test_clever_roster_fetch():
    """Clever API client should parse roster response."""
    from unittest.mock import MagicMock
    from src.integrations.clever import fetch_clever_roster

    mock_response_data = {
        "data": [
            {
                "id": "sis_001",
                "data": {
                    "name": {"first": "Alice", "last": "Smith"},
                    "email": "alice@school.com",
                },
            },
        ],
    }

    # Use MagicMock for sync methods (status_code, json()) on the response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    # Use AsyncMock for async context manager client
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_cm):
        students = await fetch_clever_roster("fake_token")
        assert len(students) == 1
        assert students[0]["first_name"] == "Alice"
        assert students[0]["last_name"] == "Smith"


@pytest.mark.asyncio
async def test_disconnect_clears_credentials(test_session):
    """Disconnecting a SIS connection should clear credentials."""
    group, owner_id = await make_test_group(test_session, name="School", group_type="school")

    conn = SISConnection(
        id=uuid4(), group_id=group.id, provider="classlink",
        credentials_encrypted=encrypt_credential("token123"),
        status="active",
    )
    test_session.add(conn)
    await test_session.flush()

    # Simulate disconnect
    conn.status = "inactive"
    conn.credentials_encrypted = None
    await test_session.flush()

    assert conn.status == "inactive"
    assert conn.credentials_encrypted is None
