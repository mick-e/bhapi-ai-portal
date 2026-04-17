"""Security tests for Intelligence Network anonymization.

Verifies that no PII leaks into distributed threat signals.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.intelligence_network.anonymizer import (
    add_dp_noise,
    anonymize_signal,
    hash_identifier,
    k_anonymize,
)
from src.intelligence_network.models import AnonymizationAudit, ThreatSignal
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Unit tests for anonymizer functions
# ---------------------------------------------------------------------------


class TestAnonymizeSignal:
    """Verify anonymize_signal strips all PII fields."""

    def test_strips_user_id(self):
        raw = {"signal_type": "test", "user_id": "u-12345"}
        result = anonymize_signal(raw)
        assert "user_id" not in result
        assert "u-12345" not in str(result)

    def test_strips_email(self):
        raw = {"signal_type": "test", "email": "alice@example.com"}
        result = anonymize_signal(raw)
        assert "email" not in result
        assert "alice@example.com" not in str(result)

    def test_strips_member_id(self):
        raw = {"signal_type": "test", "member_id": "m-99"}
        result = anonymize_signal(raw)
        assert "member_id" not in result
        assert "m-99" not in str(result)

    def test_strips_name(self):
        raw = {"signal_type": "test", "name": "Jane Smith"}
        result = anonymize_signal(raw)
        assert "name" not in result
        assert "Jane Smith" not in str(result)

    def test_strips_display_name(self):
        raw = {"signal_type": "test", "display_name": "CoolKid99"}
        result = anonymize_signal(raw)
        assert "display_name" not in result
        assert "CoolKid99" not in str(result)

    def test_strips_phone(self):
        raw = {"signal_type": "test", "phone": "+1-555-0123"}
        result = anonymize_signal(raw)
        assert "phone" not in result
        assert "+1-555-0123" not in str(result)

    def test_strips_ip_address(self):
        raw = {"signal_type": "test", "ip_address": "192.168.1.42"}
        result = anonymize_signal(raw)
        assert "ip_address" not in result
        assert "192.168.1.42" not in str(result)

    def test_strips_device_id(self):
        raw = {"signal_type": "test", "device_id": "dev-abc-123"}
        result = anonymize_signal(raw)
        assert "device_id" not in result
        assert "dev-abc-123" not in str(result)

    def test_coarsens_location_to_country(self):
        raw = {
            "signal_type": "test",
            "location": "Springfield, Illinois, United States",
        }
        result = anonymize_signal(raw)
        # Should not contain city or state
        assert "Springfield" not in str(result)
        assert "Illinois" not in str(result)
        # Country should be present
        assert result.get("contributor_region") == "United States"

    def test_generalizes_timestamp_to_hour(self):
        raw = {
            "signal_type": "test",
            "timestamp": "2026-04-16T14:37:22+00:00",
        }
        result = anonymize_signal(raw)
        # Exact timestamp must not appear
        assert "14:37:22" not in str(result)
        # Only hour-of-day should appear
        assert result.get("time_of_day") == "14:00"

    def test_preserves_non_pii_fields(self):
        raw = {
            "signal_type": "phishing",
            "severity": "high",
            "pattern_data": {"url": "evil.com"},
        }
        result = anonymize_signal(raw)
        assert result["signal_type"] == "phishing"
        assert result["severity"] == "high"
        assert result["pattern_data"] == {"url": "evil.com"}

    def test_multiple_pii_fields_stripped_simultaneously(self):
        raw = {
            "signal_type": "test",
            "user_id": "u-1",
            "email": "a@b.com",
            "member_id": "m-2",
            "name": "Bob",
            "display_name": "Bobby",
            "phone": "+1111111",
            "ip_address": "10.0.0.1",
            "device_id": "dev-x",
            "location": "NYC, NY, US",
            "timestamp": "2026-01-01T12:00:00Z",
        }
        result = anonymize_signal(raw)
        stripped = result.get("_stripped_fields", [])
        # All PII fields should be listed as stripped
        for field in ["user_id", "email", "member_id", "name", "display_name",
                       "phone", "ip_address", "device_id", "location", "timestamp"]:
            assert field in stripped, f"{field} was not stripped"

    def test_empty_event_returns_safely(self):
        result = anonymize_signal({})
        assert isinstance(result, dict)
        assert result.get("_stripped_fields") == []


# ---------------------------------------------------------------------------
# k-anonymity tests
# ---------------------------------------------------------------------------


class TestKAnonymize:
    def test_drops_groups_below_k(self):
        records = [
            {"region": "US", "type": "phishing"},
            {"region": "US", "type": "phishing"},
            {"region": "UK", "type": "malware"},  # only 1 — dropped at k=2
        ]
        result = k_anonymize(records, ["region", "type"], k=2)
        assert len(result) == 2
        assert all(r["region"] == "US" for r in result)

    def test_keeps_all_above_k(self):
        records = [{"region": "US"} for _ in range(10)]
        result = k_anonymize(records, ["region"], k=5)
        assert len(result) == 10

    def test_empty_records(self):
        assert k_anonymize([], ["x"], k=5) == []

    def test_empty_quasi_identifiers(self):
        records = [{"a": 1}]
        assert k_anonymize(records, [], k=5) == records


# ---------------------------------------------------------------------------
# Differential privacy tests
# ---------------------------------------------------------------------------


class TestDifferentialPrivacy:
    def test_noise_changes_value(self):
        """Over many runs, noise should not always be zero."""
        values = [add_dp_noise(100.0, epsilon=0.5) for _ in range(100)]
        # At least some should differ from 100
        assert not all(v == 100.0 for v in values)

    def test_noise_preserves_approximate_value(self):
        """Mean of many noised values should be close to the true value."""
        import statistics
        values = [add_dp_noise(50.0, epsilon=2.0) for _ in range(1000)]
        mean = statistics.mean(values)
        # Should be within ~5 of 50
        assert abs(mean - 50.0) < 10

    def test_zero_epsilon_raises(self):
        with pytest.raises(ValueError):
            add_dp_noise(10.0, epsilon=0)

    def test_negative_epsilon_raises(self):
        with pytest.raises(ValueError):
            add_dp_noise(10.0, epsilon=-1)


# ---------------------------------------------------------------------------
# Hash identifier tests
# ---------------------------------------------------------------------------


class TestHashIdentifier:
    def test_deterministic(self):
        h1 = hash_identifier("alice@example.com", salt="s1")
        h2 = hash_identifier("alice@example.com", salt="s1")
        assert h1 == h2

    def test_different_salt_different_hash(self):
        h1 = hash_identifier("alice@example.com", salt="s1")
        h2 = hash_identifier("alice@example.com", salt="s2")
        assert h1 != h2

    def test_original_value_not_recoverable(self):
        h = hash_identifier("secret@example.com")
        assert "secret" not in h
        assert "example.com" not in h


# ---------------------------------------------------------------------------
# E2E: verify no PII in contributed signals via HTTP
# ---------------------------------------------------------------------------


class TestNoPiiInApiResponse:
    """Verify the full HTTP contribute -> read path contains no PII."""

    @pytest_asyncio.fixture
    async def sec_engine(self):
        from sqlalchemy import event as sa_event
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import StaticPool

        from src.database import Base

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @sa_event.listens_for(engine.sync_engine, "connect")
        def set_pragma(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine
        await engine.dispose()

    @pytest_asyncio.fixture
    async def sec_session(self, sec_engine):
        from sqlalchemy.orm import sessionmaker
        maker = sessionmaker(sec_engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as session:
            yield session

    @pytest_asyncio.fixture
    async def sec_client(self, sec_engine, sec_session):
        app = create_app()
        group_id = uuid.uuid4()
        user_id = uuid.uuid4()

        async def get_db_override():
            try:
                yield sec_session
                await sec_session.commit()
            except Exception:
                await sec_session.rollback()
                raise

        async def fake_auth():
            return GroupContext(user_id=user_id, group_id=group_id, role="admin")

        app.dependency_overrides[get_db] = get_db_override
        app.dependency_overrides[get_current_user] = fake_auth

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_contribute_api_strips_pii(self, sec_client: AsyncClient):
        pii_data = {
            "signal_type": "grooming",
            "severity": "critical",
            "pattern_data": {"platform": "character_ai"},
            "user_id": "user-secret-id",
            "email": "child@family.example.com",
            "member_id": "member-secret-id",
            "name": "Alice Johnson",
            "location": "Portland, Oregon, United States",
            "timestamp": "2026-04-16T09:15:30Z",
        }

        resp = await sec_client.post(
            "/api/v1/intel-network/contribute",
            json=pii_data,
        )
        assert resp.status_code == 201
        body = resp.json()
        body_str = str(body)

        # None of these PII values should appear in the response
        assert "user-secret-id" not in body_str
        assert "child@family.example.com" not in body_str
        assert "member-secret-id" not in body_str
        assert "Alice Johnson" not in body_str
        assert "Portland" not in body_str
        assert "Oregon" not in body_str
        # Exact timestamp must not appear
        assert "09:15:30" not in body_str

    @pytest.mark.asyncio
    async def test_anonymization_audit_records_stripped_fields(
        self, sec_client: AsyncClient, sec_session: AsyncSession,
    ):
        resp = await sec_client.post(
            "/api/v1/intel-network/contribute",
            json={
                "signal_type": "test",
                "severity": "low",
                "user_id": "strip-me",
                "email": "strip@example.com",
            },
        )
        assert resp.status_code == 201
        signal_id = uuid.UUID(resp.json()["id"])

        # Check the anonymization audit
        result = await sec_session.execute(
            select(AnonymizationAudit).where(AnonymizationAudit.signal_id == signal_id)
        )
        audit = result.scalar_one_or_none()
        assert audit is not None
        assert "user_id" in audit.fields_stripped
        assert "email" in audit.fields_stripped
