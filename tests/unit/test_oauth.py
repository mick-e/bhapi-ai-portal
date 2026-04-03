"""Unit tests for OAuth helper functions."""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import ValidationError


def _make_settings(**overrides):
    """Create a mock settings object with sensible defaults."""
    defaults = {
        "oauth_google_client_id": None,
        "oauth_google_client_secret": None,
        "oauth_microsoft_client_id": None,
        "oauth_microsoft_client_secret": None,
        "oauth_apple_client_id": None,
        "oauth_apple_client_secret": None,
        "oauth_apple_team_id": None,
        "oauth_apple_key_id": None,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestGetClientId:
    """Tests for _get_client_id."""

    @patch("src.auth.oauth.settings")
    def test_google_returns_client_id(self, mock_settings):
        mock_settings.oauth_google_client_id = "google-id-123"
        from src.auth.oauth import _get_client_id

        assert _get_client_id("google") == "google-id-123"

    @patch("src.auth.oauth.settings")
    def test_microsoft_returns_client_id(self, mock_settings):
        mock_settings.oauth_microsoft_client_id = "ms-id-456"
        from src.auth.oauth import _get_client_id

        assert _get_client_id("microsoft") == "ms-id-456"

    @patch("src.auth.oauth.settings")
    def test_apple_returns_client_id(self, mock_settings):
        mock_settings.oauth_apple_client_id = "apple-id-789"
        from src.auth.oauth import _get_client_id

        assert _get_client_id("apple") == "apple-id-789"

    @patch("src.auth.oauth.settings")
    def test_unsupported_provider_raises(self, mock_settings):
        from src.auth.oauth import _get_client_id

        with pytest.raises(ValidationError, match="Unsupported OAuth provider"):
            _get_client_id("facebook")

    @patch("src.auth.oauth.settings")
    def test_unconfigured_google_raises(self, mock_settings):
        mock_settings.oauth_google_client_id = None
        from src.auth.oauth import _get_client_id

        with pytest.raises(ValidationError, match="not configured"):
            _get_client_id("google")

    @patch("src.auth.oauth.settings")
    def test_unconfigured_microsoft_raises(self, mock_settings):
        mock_settings.oauth_microsoft_client_id = None
        from src.auth.oauth import _get_client_id

        with pytest.raises(ValidationError, match="not configured"):
            _get_client_id("microsoft")

    @patch("src.auth.oauth.settings")
    def test_unconfigured_apple_raises(self, mock_settings):
        mock_settings.oauth_apple_client_id = None
        from src.auth.oauth import _get_client_id

        with pytest.raises(ValidationError, match="not configured"):
            _get_client_id("apple")

    @patch("src.auth.oauth.settings")
    def test_empty_string_client_id_raises(self, mock_settings):
        mock_settings.oauth_google_client_id = ""
        from src.auth.oauth import _get_client_id

        with pytest.raises(ValidationError, match="not configured"):
            _get_client_id("google")


class TestGetClientCredentials:
    """Tests for _get_client_credentials."""

    @patch("src.auth.oauth.settings")
    def test_google_returns_id_and_secret(self, mock_settings):
        mock_settings.oauth_google_client_id = "g-id"
        mock_settings.oauth_google_client_secret = "g-secret"
        from src.auth.oauth import _get_client_credentials

        client_id, client_secret = _get_client_credentials("google")
        assert client_id == "g-id"
        assert client_secret == "g-secret"

    @patch("src.auth.oauth.settings")
    def test_microsoft_returns_id_and_secret(self, mock_settings):
        mock_settings.oauth_microsoft_client_id = "ms-id"
        mock_settings.oauth_microsoft_client_secret = "ms-secret"
        from src.auth.oauth import _get_client_credentials

        client_id, client_secret = _get_client_credentials("microsoft")
        assert client_id == "ms-id"
        assert client_secret == "ms-secret"

    @patch("src.auth.oauth.settings")
    @patch("src.auth.oauth._generate_apple_client_secret")
    def test_apple_returns_id_and_generated_jwt(self, mock_gen, mock_settings):
        mock_settings.oauth_apple_client_id = "apple-id"
        mock_settings.oauth_apple_team_id = "TEAM123"
        mock_settings.oauth_apple_key_id = "KEY456"
        mock_settings.oauth_apple_client_secret = "-----BEGIN EC PRIVATE KEY-----\nfake"
        mock_gen.return_value = "generated-jwt-token"
        from src.auth.oauth import _get_client_credentials

        client_id, client_secret = _get_client_credentials("apple")
        assert client_id == "apple-id"
        assert client_secret == "generated-jwt-token"
        mock_gen.assert_called_once()

    @patch("src.auth.oauth.settings")
    def test_apple_missing_team_id_raises(self, mock_settings):
        mock_settings.oauth_apple_client_id = "apple-id"
        mock_settings.oauth_apple_team_id = None
        mock_settings.oauth_apple_key_id = "KEY456"
        mock_settings.oauth_apple_client_secret = "fake-key"
        from src.auth.oauth import _get_client_credentials

        with pytest.raises(ValidationError, match="Apple OAuth requires"):
            _get_client_credentials("apple")

    @patch("src.auth.oauth.settings")
    def test_apple_missing_key_id_raises(self, mock_settings):
        mock_settings.oauth_apple_client_id = "apple-id"
        mock_settings.oauth_apple_team_id = "TEAM123"
        mock_settings.oauth_apple_key_id = None
        mock_settings.oauth_apple_client_secret = "fake-key"
        from src.auth.oauth import _get_client_credentials

        with pytest.raises(ValidationError, match="Apple OAuth requires"):
            _get_client_credentials("apple")

    @patch("src.auth.oauth.settings")
    def test_apple_missing_private_key_raises(self, mock_settings):
        mock_settings.oauth_apple_client_id = "apple-id"
        mock_settings.oauth_apple_team_id = "TEAM123"
        mock_settings.oauth_apple_key_id = "KEY456"
        mock_settings.oauth_apple_client_secret = None
        from src.auth.oauth import _get_client_credentials

        with pytest.raises(ValidationError, match="Apple OAuth requires"):
            _get_client_credentials("apple")

    @patch("src.auth.oauth.settings")
    def test_google_missing_secret_raises(self, mock_settings):
        mock_settings.oauth_google_client_id = "g-id"
        mock_settings.oauth_google_client_secret = None
        from src.auth.oauth import _get_client_credentials

        with pytest.raises(ValidationError, match="not configured"):
            _get_client_credentials("google")

    @patch("src.auth.oauth.settings")
    def test_unsupported_provider_raises(self, mock_settings):
        """Unsupported provider is caught by _get_client_id before reaching credentials logic."""
        from src.auth.oauth import _get_client_credentials

        with pytest.raises(ValidationError, match="Unsupported OAuth provider"):
            _get_client_credentials("twitter")


class TestGenerateAppleClientSecret:
    """Tests for _generate_apple_client_secret."""

    @patch("src.auth.oauth.jose_jwt.encode")
    @patch("src.auth.oauth.settings")
    def test_jwt_claims_structure(self, mock_settings, mock_encode):
        mock_settings.oauth_apple_team_id = "TEAM_ABC"
        mock_settings.oauth_apple_client_id = "com.bhapi.service"
        mock_settings.oauth_apple_key_id = "KEY_XYZ"
        mock_settings.oauth_apple_client_secret = "fake-private-key"
        mock_encode.return_value = "signed-jwt"

        from src.auth.oauth import _generate_apple_client_secret

        result = _generate_apple_client_secret()
        assert result == "signed-jwt"

        # Verify jose_jwt.encode was called with correct arguments
        mock_encode.assert_called_once()
        call_args = mock_encode.call_args

        claims = call_args[0][0]
        assert claims["iss"] == "TEAM_ABC"
        assert claims["sub"] == "com.bhapi.service"
        assert claims["aud"] == "https://appleid.apple.com"
        assert "iat" in claims
        assert "exp" in claims
        # exp should be ~6 months (180 days) after iat
        assert claims["exp"] - claims["iat"] == 86400 * 180

    @patch("src.auth.oauth.jose_jwt.encode")
    @patch("src.auth.oauth.settings")
    def test_jwt_headers_have_kid_and_es256(self, mock_settings, mock_encode):
        mock_settings.oauth_apple_team_id = "TEAM_ABC"
        mock_settings.oauth_apple_client_id = "com.bhapi.service"
        mock_settings.oauth_apple_key_id = "KEY_XYZ"
        mock_settings.oauth_apple_client_secret = "fake-private-key"
        mock_encode.return_value = "signed-jwt"

        from src.auth.oauth import _generate_apple_client_secret

        _generate_apple_client_secret()

        call_args = mock_encode.call_args
        headers = call_args[1]["headers"]
        assert headers["kid"] == "KEY_XYZ"
        assert headers["alg"] == "ES256"

    @patch("src.auth.oauth.jose_jwt.encode")
    @patch("src.auth.oauth.settings")
    def test_uses_es256_algorithm(self, mock_settings, mock_encode):
        mock_settings.oauth_apple_team_id = "TEAM_ABC"
        mock_settings.oauth_apple_client_id = "com.bhapi.service"
        mock_settings.oauth_apple_key_id = "KEY_XYZ"
        mock_settings.oauth_apple_client_secret = "fake-private-key"
        mock_encode.return_value = "signed-jwt"

        from src.auth.oauth import _generate_apple_client_secret

        _generate_apple_client_secret()

        call_args = mock_encode.call_args
        assert call_args[1]["algorithm"] == "ES256"

    @patch("src.auth.oauth.jose_jwt.encode")
    @patch("src.auth.oauth.settings")
    def test_passes_private_key_to_encode(self, mock_settings, mock_encode):
        mock_settings.oauth_apple_team_id = "TEAM_ABC"
        mock_settings.oauth_apple_client_id = "com.bhapi.service"
        mock_settings.oauth_apple_key_id = "KEY_XYZ"
        mock_settings.oauth_apple_client_secret = "my-private-key-pem"
        mock_encode.return_value = "signed-jwt"

        from src.auth.oauth import _generate_apple_client_secret

        _generate_apple_client_secret()

        call_args = mock_encode.call_args
        # Second positional arg is the signing key
        assert call_args[0][1] == "my-private-key-pem"

    @patch("src.auth.oauth.jose_jwt.encode")
    @patch("src.auth.oauth.settings")
    def test_iat_is_current_time(self, mock_settings, mock_encode):
        mock_settings.oauth_apple_team_id = "TEAM_ABC"
        mock_settings.oauth_apple_client_id = "com.bhapi.service"
        mock_settings.oauth_apple_key_id = "KEY_XYZ"
        mock_settings.oauth_apple_client_secret = "fake-key"
        mock_encode.return_value = "signed-jwt"

        before = int(time.time())

        from src.auth.oauth import _generate_apple_client_secret

        _generate_apple_client_secret()

        after = int(time.time())

        call_args = mock_encode.call_args
        claims = call_args[0][0]
        assert before <= claims["iat"] <= after
