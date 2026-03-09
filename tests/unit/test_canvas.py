"""Unit tests for Canvas LMS roster sync adapter."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _mock_response(status_code, json_data, link_header=""):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = {"Link": link_header} if link_header else {}
    return resp


@pytest.mark.asyncio
async def test_canvas_parse_enrollments():
    """Canvas enrollment response is correctly parsed into roster format."""
    mock_resp = _mock_response(200, [
        {
            "user": {
                "id": 101,
                "sis_user_id": "SIS101",
                "name": "Alice Smith",
                "sortable_name": "Smith, Alice",
                "login_id": "alice@school.com",
            }
        },
        {
            "user": {
                "id": 102,
                "name": "Bob Jones",
                "sortable_name": "Jones, Bob",
                "email": "bob@school.com",
            }
        },
    ])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        roster = await fetch_canvas_roster(
            "fake-token", "https://canvas.school.com", course_id="42"
        )

    assert len(roster) == 2
    assert roster[0]["sis_id"] == "SIS101"
    assert roster[0]["first_name"] == "Alice"
    assert roster[0]["last_name"] == "Smith"
    assert roster[0]["email"] == "alice@school.com"
    assert roster[0]["role"] == "member"
    # Second user has no sis_user_id, falls back to id; no login_id, falls back to email
    assert roster[1]["sis_id"] == "102"
    assert roster[1]["email"] == "bob@school.com"


@pytest.mark.asyncio
async def test_canvas_direct_users():
    """Canvas account users endpoint (no course_id) parses direct user objects."""
    mock_resp = _mock_response(200, [
        {
            "id": 201,
            "sis_user_id": "SIS201",
            "name": "Charlie Brown",
            "sortable_name": "Brown, Charlie",
            "login_id": "charlie@school.com",
        },
    ])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        roster = await fetch_canvas_roster("fake-token", "https://canvas.school.com")

    assert len(roster) == 1
    assert roster[0]["sis_id"] == "SIS201"
    assert roster[0]["first_name"] == "Charlie"
    assert roster[0]["last_name"] == "Brown"


@pytest.mark.asyncio
async def test_canvas_pagination():
    """Canvas Link header pagination fetches multiple pages."""
    page1_resp = _mock_response(
        200,
        [{"id": 1, "name": "Page One", "sortable_name": "One, Page", "login_id": "p1@school.com"}],
        link_header='<https://canvas.school.com/api/v1/accounts/self/users?page=2>; rel="next"',
    )
    page2_resp = _mock_response(
        200,
        [{"id": 2, "name": "Page Two", "sortable_name": "Two, Page", "login_id": "p2@school.com"}],
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=[page1_resp, page2_resp])
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        roster = await fetch_canvas_roster("fake-token", "https://canvas.school.com")

    assert len(roster) == 2
    assert roster[0]["sis_id"] == "1"
    assert roster[1]["sis_id"] == "2"


@pytest.mark.asyncio
async def test_canvas_api_error():
    """Canvas API error raises ValueError."""
    mock_resp = _mock_response(401, {})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        with pytest.raises(ValueError, match="Invalid Canvas access token"):
            await fetch_canvas_roster("bad-token")


@pytest.mark.asyncio
async def test_canvas_server_error():
    """Canvas non-401 error raises ValueError with status code."""
    mock_resp = _mock_response(503, {})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        with pytest.raises(ValueError, match="Canvas API error: 503"):
            await fetch_canvas_roster("fake-token")


@pytest.mark.asyncio
async def test_canvas_empty_roster():
    """Canvas returns empty roster when no enrollments."""
    mock_resp = _mock_response(200, [])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from src.integrations.canvas import fetch_canvas_roster

        roster = await fetch_canvas_roster("fake-token")

    assert len(roster) == 0
