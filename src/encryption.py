"""Credential encryption — Fernet (dev/test) or Cloud KMS (production).

Usage:
    from src.encryption import encrypt_credential, decrypt_credential

    encrypted = encrypt_credential("sk-abc123...")
    plaintext = decrypt_credential(encrypted)
"""

import base64
import hashlib

import structlog
from cryptography.fernet import Fernet

from src.config import get_settings

logger = structlog.get_logger()

# Module-level cache for the Fernet instance
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet instance derived from SECRET_KEY."""
    global _fernet
    if _fernet is None:
        settings = get_settings()
        # Derive a 32-byte key from SECRET_KEY using SHA-256, then base64-encode
        key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        _fernet = Fernet(fernet_key)
    return _fernet


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a credential string.

    In production with GCP_PROJECT_ID set, uses Cloud KMS.
    Otherwise falls back to Fernet derived from SECRET_KEY.

    Returns a prefixed string: "fernet:<token>" or "kms:<ciphertext>".
    """
    settings = get_settings()

    if settings.is_production and settings.gcp_project_id:
        return _kms_encrypt(plaintext, settings.gcp_project_id)

    token = _get_fernet().encrypt(plaintext.encode()).decode()
    return f"fernet:{token}"


def decrypt_credential(encrypted: str) -> str:
    """Decrypt a credential string.

    Detects the prefix to choose the right decryption method.
    Falls back to treating unprefixed values as plaintext (migration path).
    """
    if encrypted.startswith("fernet:"):
        token = encrypted[len("fernet:"):]
        return _get_fernet().decrypt(token.encode()).decode()

    if encrypted.startswith("kms:"):
        settings = get_settings()
        if not settings.gcp_project_id:
            raise ValueError("Cannot decrypt KMS credential without GCP_PROJECT_ID")
        return _kms_decrypt(encrypted[len("kms:"):], settings.gcp_project_id)

    # Unprefixed = legacy plaintext — return as-is for backward compatibility
    logger.warning("decrypt_legacy_plaintext", msg="Credential stored without encryption prefix")
    return encrypted


# ---------------------------------------------------------------------------
# Cloud KMS helpers (stubbed — requires google-cloud-kms in production)
# ---------------------------------------------------------------------------

_KMS_KEY_RING = "bhapi-keys"
_KMS_KEY_NAME = "credential-key"
_KMS_LOCATION = "global"


def _kms_encrypt(plaintext: str, project_id: str) -> str:
    """Encrypt using Google Cloud KMS."""
    try:
        from google.cloud import kms  # type: ignore[import-untyped]

        client = kms.KeyManagementServiceClient()
        key_name = client.crypto_key_path(
            project_id, _KMS_LOCATION, _KMS_KEY_RING, _KMS_KEY_NAME
        )
        response = client.encrypt(
            request={"name": key_name, "plaintext": plaintext.encode()}
        )
        ciphertext_b64 = base64.b64encode(response.ciphertext).decode()
        return f"kms:{ciphertext_b64}"
    except ImportError:
        logger.error("kms_import_error", msg="google-cloud-kms not installed, falling back to Fernet")
        token = _get_fernet().encrypt(plaintext.encode()).decode()
        return f"fernet:{token}"


def _kms_decrypt(ciphertext_b64: str, project_id: str) -> str:
    """Decrypt using Google Cloud KMS."""
    from google.cloud import kms  # type: ignore[import-untyped]

    client = kms.KeyManagementServiceClient()
    key_name = client.crypto_key_path(
        project_id, _KMS_LOCATION, _KMS_KEY_RING, _KMS_KEY_NAME
    )
    ciphertext = base64.b64decode(ciphertext_b64)
    response = client.decrypt(
        request={"name": key_name, "ciphertext": ciphertext}
    )
    return response.plaintext.decode()
