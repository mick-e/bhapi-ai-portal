"""Unit tests for PowerSchool SIS adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_powerschool_parse_roster():
    """PowerSchool API response is correctly parsed into roster format."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "students": {
            "student": [
                {
                    "id": 12345,
                    "name": {"first_name": "Alice", "last_name": "Smith"},
                    "emails": {"email": [{"emailAddress": "alice@school.com"}]},
                },
                {
                    "id": 67890,
                    "name": {"first_name": "Bob", "last_name": "Jones"},
                    "emails": {"email": {"emailAddress": "bob@school.com"}},
                },
            ]
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from src.integrations.powerschool import fetch_powerschool_roster

        roster = await fetch_powerschool_roster("fake-token", "https://ps.school.com")

    assert len(roster) == 2
    assert roster[0]["sis_id"] == "12345"
    assert roster[0]["first_name"] == "Alice"
    assert roster[0]["last_name"] == "Smith"
    assert roster[0]["email"] == "alice@school.com"
    assert roster[0]["role"] == "member"
    # Second student has single email dict (not list)
    assert roster[1]["sis_id"] == "67890"
    assert roster[1]["first_name"] == "Bob"
    assert roster[1]["email"] == "bob@school.com"


@pytest.mark.asyncio
async def test_powerschool_single_student():
    """PowerSchool single student result (dict instead of list) is handled."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "students": {
            "student": {
                "id": 11111,
                "name": {"first_name": "Solo", "last_name": "Kid"},
                "emails": {"email": {"emailAddress": "solo@school.com"}},
            }
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from src.integrations.powerschool import fetch_powerschool_roster

        roster = await fetch_powerschool_roster("fake-token")

    assert len(roster) == 1
    assert roster[0]["sis_id"] == "11111"
    assert roster[0]["first_name"] == "Solo"


@pytest.mark.asyncio
async def test_powerschool_api_error():
    """PowerSchool API error raises ValueError."""
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from src.integrations.powerschool import fetch_powerschool_roster

        with pytest.raises(ValueError, match="Invalid PowerSchool access token"):
            await fetch_powerschool_roster("bad-token")


@pytest.mark.asyncio
async def test_powerschool_server_error():
    """PowerSchool non-401 error raises ValueError with status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from src.integrations.powerschool import fetch_powerschool_roster

        with pytest.raises(ValueError, match="PowerSchool API error: 500"):
            await fetch_powerschool_roster("fake-token")


@pytest.mark.asyncio
async def test_powerschool_empty_roster():
    """PowerSchool returns empty roster when no students."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"students": {"student": []}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        from src.integrations.powerschool import fetch_powerschool_roster

        roster = await fetch_powerschool_roster("fake-token")

    assert len(roster) == 0
