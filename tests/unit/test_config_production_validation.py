"""Production config must fail closed on weak or missing security settings."""

import pytest

from src.config import Settings


def _prod_env(**overrides):
    base = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql+asyncpg://bhapi:strongpw123456@db.example.com:5432/bhapi",
        "SECRET_KEY": "a" * 48,
        "CAPTURE_HMAC_ENABLED": "true",
        "CAPTURE_HMAC_SECRET": "b" * 48,
    }
    base.update(overrides)
    return base


def test_production_rejects_dev_default_secret(monkeypatch):
    env = _prod_env(SECRET_KEY="dev-secret-key-change-in-production")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings().validate_production_config()


def test_production_rejects_missing_hmac_when_not_enabled(monkeypatch):
    env = _prod_env(CAPTURE_HMAC_ENABLED="false")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = Settings()
    with pytest.raises(ValueError, match="CAPTURE_HMAC_ENABLED"):
        s.validate_production_config()


def test_production_rejects_hmac_enabled_without_secret(monkeypatch):
    env = _prod_env(CAPTURE_HMAC_ENABLED="true", CAPTURE_HMAC_SECRET="")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = Settings()
    with pytest.raises(ValueError, match="CAPTURE_HMAC_SECRET"):
        s.validate_production_config()


def test_production_accepts_fully_configured(monkeypatch):
    env = _prod_env()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    Settings().validate_production_config()  # no raise
