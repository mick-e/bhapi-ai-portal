"""Unit tests for content excerpt encryption round-trip."""

from src.encryption import encrypt_credential, decrypt_credential


def test_short_content_roundtrip():
    content = "Hello"
    assert decrypt_credential(encrypt_credential(content)) == content


def test_long_content_roundtrip():
    content = "x" * 4000
    assert decrypt_credential(encrypt_credential(content)) == content


def test_unicode_content_roundtrip():
    content = "Bonjour le monde! Hola mundo! \u2603 \U0001f600"
    assert decrypt_credential(encrypt_credential(content)) == content


def test_empty_string_roundtrip():
    content = ""
    assert decrypt_credential(encrypt_credential(content)) == content


def test_special_chars_roundtrip():
    content = '<script>alert("xss")</script> & "quotes" \' apostrophe'
    assert decrypt_credential(encrypt_credential(content)) == content
