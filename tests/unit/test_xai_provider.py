"""Unit tests for xAI spend provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.billing.providers.xai_client import XAIProvider
from src.billing.providers.base import AuthenticationError


@pytest.mark.asyncio
async def test_xai_validate_credentials():
    """XAI credential validation should call /v1/models."""
    provider = XAIProvider(api_key="xai-test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.validate_credentials()
        assert result is True


@pytest.mark.asyncio
async def test_xai_invalid_credentials():
    """Invalid credentials should return False."""
    provider = XAIProvider(api_key="invalid")

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.validate_credentials()
        assert result is False


@pytest.mark.asyncio
async def test_xai_fetch_usage_auth_error():
    """Authentication error should raise AuthenticationError."""
    provider = XAIProvider(api_key="bad-key")

    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        with pytest.raises(AuthenticationError, match="Invalid xAI"):
            now = datetime.now(timezone.utc)
            await provider.fetch_usage(now, now)


@pytest.mark.asyncio
async def test_xai_fetch_usage_success():
    """Successful fetch should return SpendEntry list."""
    provider = XAIProvider(api_key="xai-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"cost": 1.50, "model": "grok-2", "total_tokens": 1000},
            {"cost": 0.0, "model": "grok-2"},  # Zero cost filtered out
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        now = datetime.now(timezone.utc)
        entries = await provider.fetch_usage(now, now)
        assert len(entries) == 1
        assert entries[0].amount == 1.5
        assert entries[0].model == "grok-2"
