"""Security tests for content excerpt encryption at rest."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.encryption import decrypt_credential, encrypt_credential
from src.risk.models import ContentExcerpt
from tests.conftest import make_test_group


def test_encrypt_decrypt_roundtrip():
    """Content should survive encrypt/decrypt round-trip."""
    plaintext = "This is sensitive AI interaction content with PII: John Doe, SSN 123-45-6789"
    encrypted = encrypt_credential(plaintext)
    assert encrypted != plaintext
    assert encrypted.startswith("fernet:")
    decrypted = decrypt_credential(encrypted)
    assert decrypted == plaintext


def test_encrypted_content_not_plaintext():
    """Encrypted content should not contain the original plaintext."""
    plaintext = "sensitive content about self-harm"
    encrypted = encrypt_credential(plaintext)
    assert plaintext not in encrypted


def test_different_inputs_produce_different_ciphertexts():
    """Different inputs should produce different encrypted values."""
    a = encrypt_credential("content A")
    b = encrypt_credential("content B")
    assert a != b


@pytest.mark.asyncio
async def test_content_excerpt_stores_encrypted(test_session):
    """ContentExcerpt should store encrypted, not plaintext content."""
    from src.groups.models import GroupMember
    from src.risk.models import RiskEvent

    group, owner_id = await make_test_group(test_session, name="Test", group_type="family")
    member = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="parent", display_name="P")
    test_session.add(member)
    await test_session.flush()

    risk_event = RiskEvent(
        id=uuid4(), group_id=group.id, member_id=member.id,
        category="self_harm", severity="high", confidence=0.9,
        details={}, acknowledged=False,
    )
    test_session.add(risk_event)
    await test_session.flush()

    plaintext = "Child asked about dangerous topics"
    encrypted = encrypt_credential(plaintext)

    excerpt = ContentExcerpt(
        id=uuid4(), risk_event_id=risk_event.id,
        encrypted_content=encrypted,
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    test_session.add(excerpt)
    await test_session.flush()

    # Verify DB stores encrypted, not plaintext
    assert excerpt.encrypted_content.startswith("fernet:")
    assert plaintext not in excerpt.encrypted_content

    # Verify we can decrypt
    decrypted = decrypt_credential(excerpt.encrypted_content)
    assert decrypted == plaintext
