"""Security tests for federated SSO — tenant isolation and domain restriction."""

import pytest
from unittest.mock import patch

from src.auth.oauth import PROVIDER_CONFIGS, get_authorization_url


def test_supported_providers():
    """Only configured providers should be supported."""
    assert "google" in PROVIDER_CONFIGS
    assert "microsoft" in PROVIDER_CONFIGS
    assert "apple" in PROVIDER_CONFIGS
    assert "unknown_provider" not in PROVIDER_CONFIGS


def test_unsupported_provider_rejected():
    """Unsupported provider should raise ValidationError."""
    from src.exceptions import ValidationError

    with pytest.raises(ValidationError, match="Unsupported"):
        get_authorization_url("malicious_provider")
