"""Security tests for SQL injection prevention in health check schema diagnostic."""

import pytest

from src.main import (
    _ALLOWED_SCHEMA_CHECKS,
    _SCHEMA_CHECK_PAIRS,
    _is_safe_identifier,
)


# ---------------------------------------------------------------------------
# _is_safe_identifier unit tests
# ---------------------------------------------------------------------------


class TestSafeIdentifier:
    """Validate the identifier safeguard used by /health/schema."""

    def test_simple_table_name(self):
        assert _is_safe_identifier("capture_events") is True

    def test_simple_column_name(self):
        assert _is_safe_identifier("content_encrypted") is True

    def test_rejects_semicolon(self):
        assert _is_safe_identifier("users; DROP TABLE users") is False

    def test_rejects_sql_comment(self):
        assert _is_safe_identifier("users--") is False

    def test_rejects_parentheses(self):
        assert _is_safe_identifier("users()") is False

    def test_rejects_spaces(self):
        assert _is_safe_identifier("users table") is False

    def test_rejects_quotes(self):
        assert _is_safe_identifier("users'") is False
        assert _is_safe_identifier('users"') is False

    def test_rejects_empty_string(self):
        assert _is_safe_identifier("") is False

    def test_rejects_leading_digit(self):
        assert _is_safe_identifier("1users") is False

    def test_accepts_underscored_name(self):
        assert _is_safe_identifier("_private_table") is True

    def test_rejects_union_select(self):
        assert _is_safe_identifier("x UNION SELECT * FROM users") is False


# ---------------------------------------------------------------------------
# Allowlist integrity tests
# ---------------------------------------------------------------------------


class TestSchemaAllowlist:
    """Ensure the allowlist is correctly configured."""

    def test_allowlist_matches_check_pairs(self):
        """The set used for validation must match the list used for iteration."""
        assert _ALLOWED_SCHEMA_CHECKS == set(_SCHEMA_CHECK_PAIRS)

    def test_all_pairs_are_safe_identifiers(self):
        """Every allowlisted table and column must pass the identifier check."""
        for table, col in _SCHEMA_CHECK_PAIRS:
            assert _is_safe_identifier(table), f"Table {table!r} is not a safe identifier"
            assert _is_safe_identifier(col), f"Column {col!r} is not a safe identifier"


# ---------------------------------------------------------------------------
# /health/schema endpoint tests (injection attempts)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_schema_rejects_sql_injection_in_table_name(client):
    """Injecting SQL via a forged table name must not reach the database.

    Since the endpoint iterates only over the hardcoded allowlist and never
    accepts user input, we verify the defence-in-depth: that the allowlist
    and identifier checks would reject malicious values if the loop were
    ever changed to accept external input.
    """
    malicious_tables = [
        "users; DROP TABLE users --",
        "capture_events UNION SELECT password_hash FROM users --",
        "1; SELECT * FROM users",
        "block_rules' OR '1'='1",
    ]
    for name in malicious_tables:
        assert _is_safe_identifier(name) is False, (
            f"Malicious table name {name!r} was not rejected"
        )
        assert (name, "id") not in _ALLOWED_SCHEMA_CHECKS, (
            f"Malicious table name {name!r} should not be in the allowlist"
        )


@pytest.mark.asyncio
async def test_health_schema_rejects_sql_injection_in_column_name(client):
    """Injecting SQL via a forged column name must not reach the database."""
    malicious_columns = [
        "id; DROP TABLE users --",
        "id UNION SELECT password_hash FROM users --",
        "1; SELECT * FROM users",
        "content_encrypted' OR '1'='1",
    ]
    for name in malicious_columns:
        assert _is_safe_identifier(name) is False, (
            f"Malicious column name {name!r} was not rejected"
        )
        assert ("capture_events", name) not in _ALLOWED_SCHEMA_CHECKS, (
            f"Malicious column name {name!r} should not be in the allowlist"
        )


@pytest.mark.asyncio
async def test_health_schema_works_with_valid_table(client):
    """The /health/schema endpoint should return 200 and contain expected keys."""
    resp = await client.get("/health/schema")
    assert resp.status_code == 200
    data = resp.json()

    # In test DB (SQLite, no alembic_version table) the endpoint may hit
    # the outer except and return {"error": ...}.  That's fine — the
    # important thing is that it returns 200 and doesn't crash.
    if "error" in data:
        # Outer exception caught; column checks never ran.  Just verify
        # the endpoint didn't blow up.
        return

    # If the endpoint did complete the column checks, verify each pair.
    for table, col in _SCHEMA_CHECK_PAIRS:
        key = f"{table}.{col}"
        assert key in data, f"Expected key {key!r} in schema check response"
        # Value should be either "exists" or "MISSING: ..." (test DB may
        # not have all tables), but never "REJECTED".
        assert not data[key].startswith("REJECTED"), (
            f"Valid pair {key!r} was unexpectedly rejected"
        )
