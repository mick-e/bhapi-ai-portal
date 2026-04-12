"""Unit tests for auth service token replay tracking."""

import pytest

from src.auth.service import (
    _fallback_used_tokens,
    _is_token_used,
    _mark_token_used,
)


@pytest.fixture(autouse=True)
def _clear_fallback_tokens():
    """Clear the in-memory fallback set between tests."""
    _fallback_used_tokens.clear()
    yield
    _fallback_used_tokens.clear()


@pytest.mark.asyncio
async def test_mark_and_check_token_used():
    """Token marked as used should be detected on subsequent check."""
    assert not await _is_token_used("reset", "tok-1")
    await _mark_token_used("reset", "tok-1")
    assert await _is_token_used("reset", "tok-1")


@pytest.mark.asyncio
async def test_different_categories_are_independent():
    """Tokens in different categories should not collide."""
    await _mark_token_used("reset", "tok-shared")
    assert await _is_token_used("reset", "tok-shared")
    assert not await _is_token_used("approval", "tok-shared")


@pytest.mark.asyncio
async def test_unused_token_is_not_found():
    """A token that was never marked should not be found."""
    assert not await _is_token_used("reset", "never-used")
    assert not await _is_token_used("approval", "never-used")


@pytest.mark.asyncio
async def test_multiple_tokens_tracked_independently():
    """Multiple tokens in the same category are tracked independently."""
    await _mark_token_used("reset", "a")
    await _mark_token_used("reset", "b")
    assert await _is_token_used("reset", "a")
    assert await _is_token_used("reset", "b")
    assert not await _is_token_used("reset", "c")


@pytest.mark.asyncio
async def test_fallback_key_format():
    """Verify the in-memory fallback uses the expected key format."""
    await _mark_token_used("reset", "jti-123")
    assert "bhapi:used_token:reset:jti-123" in _fallback_used_tokens
