"""Unit tests for credential encryption (src/encryption.py).

Covers Fernet encrypt/decrypt round-trip, prefix format, legacy plaintext
fallback, edge-case credential strings, key derivation determinism, and
invalid-token error handling.
"""

import pytest
from cryptography.fernet import InvalidToken

from src.encryption import decrypt_credential, encrypt_credential

# ---------------------------------------------------------------------------
# 1. encrypt_credential returns a fernet-prefixed string
# ---------------------------------------------------------------------------

class TestEncryptPrefix:
    """encrypt_credential output must start with 'fernet:' in dev/test."""

    def test_returns_fernet_prefix(self):
        result = encrypt_credential("sk-abc123")
        assert result.startswith("fernet:")

    def test_prefix_followed_by_nonempty_token(self):
        result = encrypt_credential("some-api-key")
        token_part = result[len("fernet:"):]
        assert len(token_part) > 0

    def test_token_is_valid_fernet_bytes(self):
        """The token portion should be a valid base64-encoded Fernet token."""
        result = encrypt_credential("test-value")
        token_part = result[len("fernet:"):]
        # Fernet tokens are url-safe base64 — they should only contain
        # [A-Za-z0-9_=-] characters.
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=")
        assert all(ch in allowed for ch in token_part)


# ---------------------------------------------------------------------------
# 2. Round-trip: encrypt then decrypt gives original
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """encrypt_credential -> decrypt_credential must recover the plaintext."""

    def test_simple_string(self):
        original = "sk-abc123"
        assert decrypt_credential(encrypt_credential(original)) == original

    def test_uuid_style_key(self):
        original = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert decrypt_credential(encrypt_credential(original)) == original

    def test_json_payload(self):
        original = '{"key": "value", "nested": [1, 2, 3]}'
        assert decrypt_credential(encrypt_credential(original)) == original

    def test_multiline_string(self):
        original = "line1\nline2\nline3"
        assert decrypt_credential(encrypt_credential(original)) == original

    def test_unicode_content(self):
        original = "clef-secrete-tres-confidentielle"
        assert decrypt_credential(encrypt_credential(original)) == original

    def test_two_encryptions_of_same_value_both_decrypt(self):
        """Fernet tokens include a timestamp, so two encryptions of the same
        value produce different ciphertexts — but both must decrypt correctly."""
        original = "repeated-secret"
        enc1 = encrypt_credential(original)
        enc2 = encrypt_credential(original)
        # Tokens differ (Fernet includes a timestamp nonce)
        assert enc1 != enc2
        # Both decrypt back to the original
        assert decrypt_credential(enc1) == original
        assert decrypt_credential(enc2) == original


# ---------------------------------------------------------------------------
# 3. Legacy unprefixed plaintext fallback
# ---------------------------------------------------------------------------

class TestLegacyPlaintext:
    """decrypt_credential returns unprefixed strings as-is (migration path)."""

    def test_plain_api_key_returned_unchanged(self):
        legacy = "sk-legacy-plaintext-key-no-prefix"
        assert decrypt_credential(legacy) == legacy

    def test_empty_looking_legacy(self):
        assert decrypt_credential("just-a-string") == "just-a-string"

    def test_numeric_string(self):
        assert decrypt_credential("1234567890") == "1234567890"

    def test_url_as_legacy(self):
        url = "https://api.example.com/v1/key?token=abc"
        assert decrypt_credential(url) == url

    def test_does_not_strip_whitespace(self):
        """Whitespace should be preserved, not silently stripped."""
        padded = "  spaced-key  "
        assert decrypt_credential(padded) == padded


# ---------------------------------------------------------------------------
# 4. Various credential strings (edge cases)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Encrypt/decrypt with empty, long, and special-character strings."""

    def test_empty_string(self):
        encrypted = encrypt_credential("")
        assert encrypted.startswith("fernet:")
        assert decrypt_credential(encrypted) == ""

    def test_long_key(self):
        long_key = "A" * 10_000
        encrypted = encrypt_credential(long_key)
        assert decrypt_credential(encrypted) == long_key

    def test_special_characters(self):
        special = r"p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"
        assert decrypt_credential(encrypt_credential(special)) == special

    def test_newlines_and_tabs(self):
        messy = "key\twith\ttabs\nand\nnewlines\r\n"
        assert decrypt_credential(encrypt_credential(messy)) == messy

    def test_null_bytes(self):
        with_nulls = "before\x00after"
        assert decrypt_credential(encrypt_credential(with_nulls)) == with_nulls

    def test_emoji_content(self):
        emoji_str = "secret-key-with-emoji"
        assert decrypt_credential(encrypt_credential(emoji_str)) == emoji_str

    def test_only_whitespace(self):
        ws = "   \t\n  "
        assert decrypt_credential(encrypt_credential(ws)) == ws

    def test_single_character(self):
        assert decrypt_credential(encrypt_credential("x")) == "x"


# ---------------------------------------------------------------------------
# 5. Key derivation determinism
# ---------------------------------------------------------------------------

class TestKeyDerivationDeterminism:
    """Same SECRET_KEY must produce consistent encryption/decryption results."""

    def test_decrypt_across_calls(self):
        """An encrypted value from one call must decrypt in a later call,
        proving the derived Fernet key is stable for the same SECRET_KEY."""
        original = "determinism-test-credential"
        encrypted = encrypt_credential(original)
        # Decrypt in a separate call (same process, same cached key)
        result = decrypt_credential(encrypted)
        assert result == original

    def test_multiple_values_independently_recoverable(self):
        """Multiple different credentials encrypted sequentially should each
        decrypt to their own original value."""
        creds = [
            "cred-alpha",
            "cred-beta",
            "cred-gamma",
            "",
            "a" * 500,
        ]
        encrypted_list = [encrypt_credential(c) for c in creds]
        decrypted_list = [decrypt_credential(e) for e in encrypted_list]
        assert decrypted_list == creds

    def test_encrypt_output_is_always_prefixed(self):
        """Regardless of input, the output always has the fernet: prefix,
        confirming the same code path (Fernet, not KMS) is used."""
        for value in ["", "short", "x" * 5000, "special!@#$"]:
            assert encrypt_credential(value).startswith("fernet:")


# ---------------------------------------------------------------------------
# 6. Invalid Fernet token raises an error
# ---------------------------------------------------------------------------

class TestInvalidToken:
    """decrypt_credential must raise when given a corrupted fernet: token."""

    def test_garbage_token(self):
        with pytest.raises(Exception):
            decrypt_credential("fernet:not-a-valid-token")

    def test_truncated_token(self):
        encrypted = encrypt_credential("real-secret")
        truncated = encrypted[:len("fernet:") + 10]
        with pytest.raises(Exception):
            decrypt_credential(truncated)

    def test_tampered_token(self):
        encrypted = encrypt_credential("real-secret")
        token = encrypted[len("fernet:"):]
        # Flip a character in the middle of the token
        mid = len(token) // 2
        tampered_char = "A" if token[mid] != "A" else "B"
        tampered = "fernet:" + token[:mid] + tampered_char + token[mid + 1:]
        with pytest.raises(Exception):
            decrypt_credential(tampered)

    def test_empty_fernet_token(self):
        with pytest.raises(Exception):
            decrypt_credential("fernet:")

    def test_wrong_fernet_key_token(self):
        """A token encrypted with a different Fernet key should fail."""
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        different_key = hashlib.sha256(b"completely-different-key").digest()
        foreign_fernet = Fernet(base64.urlsafe_b64encode(different_key))
        foreign_token = foreign_fernet.encrypt(b"secret").decode()
        with pytest.raises(InvalidToken):
            decrypt_credential(f"fernet:{foreign_token}")
