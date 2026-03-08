"""Security tests for SIS credential encryption at rest."""

import pytest
from uuid import uuid4

from src.encryption import encrypt_credential, decrypt_credential
from src.integrations.models import SISConnection
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_sis_credentials_encrypted_in_db(test_session):
    """SIS credentials must be encrypted before storage."""
    group, owner_id = await make_test_group(test_session, name="School", group_type="school")

    plaintext_token = "clever_access_token_abc123"
    encrypted = encrypt_credential(plaintext_token)

    conn = SISConnection(
        id=uuid4(),
        group_id=group.id,
        provider="clever",
        credentials_encrypted=encrypted,
        status="active",
    )
    test_session.add(conn)
    await test_session.flush()

    # DB value should be encrypted
    assert conn.credentials_encrypted.startswith("fernet:")
    assert plaintext_token not in conn.credentials_encrypted

    # Should decrypt correctly
    decrypted = decrypt_credential(conn.credentials_encrypted)
    assert decrypted == plaintext_token
