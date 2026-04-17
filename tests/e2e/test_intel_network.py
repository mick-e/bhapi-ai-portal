"""End-to-end tests for the Intelligence Network module."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group
from src.intelligence_network.models import ThreatSignal
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    maker = sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_user(e2e_session):
    user = User(
        id=uuid.uuid4(),
        email=f"intel-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Intel User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def e2e_group(e2e_session, e2e_user):
    group = Group(
        id=uuid.uuid4(),
        name="Intel Family",
        type="family",
        owner_id=e2e_user.id,
        settings={},
    )
    e2e_session.add(group)
    await e2e_session.flush()
    return group


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
    """Create an authenticated test client."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role="admin")

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def intel_client(e2e_engine, e2e_session, e2e_user, e2e_group):
    async with _make_client(e2e_engine, e2e_session, e2e_user.id, e2e_group.id) as c:
        yield c


# ---------------------------------------------------------------------------
# Subscription lifecycle
# ---------------------------------------------------------------------------


class TestSubscriptionLifecycle:
    @pytest.mark.asyncio
    async def test_subscribe_returns_201(self, intel_client: AsyncClient):
        resp = await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"signal_types": ["phishing", "deepfake"], "minimum_severity": "high"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert data["signal_types"] == ["phishing", "deepfake"]
        assert data["minimum_severity"] == "high"

    @pytest.mark.asyncio
    async def test_get_subscription(self, intel_client: AsyncClient):
        # Subscribe first
        await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "low"},
        )
        resp = await intel_client.get("/api/v1/intel-network/subscription")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, intel_client: AsyncClient):
        resp = await intel_client.get("/api/v1/intel-network/subscription")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unsubscribe(self, intel_client: AsyncClient):
        await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "medium"},
        )
        resp = await intel_client.delete("/api/v1/intel-network/subscribe")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_unsubscribe_without_subscription_returns_404(self, intel_client: AsyncClient):
        resp = await intel_client.delete("/api/v1/intel-network/subscribe")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_resubscribe_after_unsubscribe(self, intel_client: AsyncClient):
        # Subscribe
        resp1 = await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "low"},
        )
        assert resp1.status_code == 201

        # Unsubscribe
        await intel_client.delete("/api/v1/intel-network/subscribe")

        # Resubscribe
        resp2 = await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "high"},
        )
        assert resp2.status_code == 201
        assert resp2.json()["is_active"] is True
        assert resp2.json()["minimum_severity"] == "high"


# ---------------------------------------------------------------------------
# Contribute signals
# ---------------------------------------------------------------------------


class TestContributeSignal:
    @pytest.mark.asyncio
    async def test_contribute_returns_201(self, intel_client: AsyncClient):
        resp = await intel_client.post(
            "/api/v1/intel-network/contribute",
            json={
                "signal_type": "phishing",
                "severity": "high",
                "pattern_data": {"url_pattern": "*.evil.example.com"},
                "description": "Phishing attempt via AI chatbot",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["signal_type"] == "phishing"
        assert data["severity"] == "high"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_contribute_strips_pii(self, intel_client: AsyncClient):
        resp = await intel_client.post(
            "/api/v1/intel-network/contribute",
            json={
                "signal_type": "data_exfil",
                "severity": "critical",
                "pattern_data": {"method": "clipboard"},
                "user_id": "should-be-stripped",
                "email": "victim@example.com",
                "member_id": "member-123",
                "name": "John Doe",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        # PII must not appear in the response
        pattern = data.get("pattern_data", {})
        all_values = str(data)
        assert "should-be-stripped" not in all_values
        assert "victim@example.com" not in all_values
        assert "member-123" not in all_values
        assert "John Doe" not in all_values

    @pytest.mark.asyncio
    async def test_contribute_invalid_severity(self, intel_client: AsyncClient):
        resp = await intel_client.post(
            "/api/v1/intel-network/contribute",
            json={
                "signal_type": "test",
                "severity": "super-critical",
                "pattern_data": {},
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Signal feed
# ---------------------------------------------------------------------------


class TestSignalFeed:
    @pytest.mark.asyncio
    async def test_feed_requires_subscription(self, intel_client: AsyncClient):
        resp = await intel_client.get("/api/v1/intel-network/feed")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_feed_returns_signals_above_threshold(
        self, intel_client: AsyncClient, e2e_session
    ):
        # Subscribe
        await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "medium"},
        )

        # Seed signals with sample_size >= 5 directly in DB
        for i in range(3):
            signal = ThreatSignal(
                id=uuid.uuid4(),
                signal_type="malware",
                severity="high",
                pattern_data={"variant": f"v{i}"},
                sample_size=10,
                confidence=0.8,
            )
            e2e_session.add(signal)
        await e2e_session.flush()
        await e2e_session.commit()

        resp = await intel_client.get("/api/v1/intel-network/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all(s["sample_size"] >= 5 for s in data)

    @pytest.mark.asyncio
    async def test_feed_filters_by_severity(
        self, intel_client: AsyncClient, e2e_session
    ):
        # Subscribe with high minimum
        await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "high"},
        )

        # Add signals of different severities
        for sev in ["low", "medium", "high", "critical"]:
            signal = ThreatSignal(
                id=uuid.uuid4(),
                signal_type="test",
                severity=sev,
                pattern_data={},
                sample_size=10,
                confidence=0.5,
            )
            e2e_session.add(signal)
        await e2e_session.flush()
        await e2e_session.commit()

        resp = await intel_client.get("/api/v1/intel-network/feed")
        assert resp.status_code == 200
        data = resp.json()
        severities = {s["severity"] for s in data}
        assert "low" not in severities
        assert "medium" not in severities

    @pytest.mark.asyncio
    async def test_feed_excludes_below_k_threshold(
        self, intel_client: AsyncClient, e2e_session
    ):
        # Subscribe
        await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "low"},
        )

        # Signal with sample_size < 5 should be excluded
        low_k = ThreatSignal(
            id=uuid.uuid4(),
            signal_type="rare",
            severity="high",
            pattern_data={},
            sample_size=2,
            confidence=0.9,
        )
        e2e_session.add(low_k)
        await e2e_session.flush()
        await e2e_session.commit()

        resp = await intel_client.get("/api/v1/intel-network/feed")
        assert resp.status_code == 200
        data = resp.json()
        ids = [s["id"] for s in data]
        assert str(low_k.id) not in ids


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class TestFeedback:
    @pytest.mark.asyncio
    async def test_submit_helpful_feedback(
        self, intel_client: AsyncClient, e2e_session
    ):
        signal = ThreatSignal(
            id=uuid.uuid4(),
            signal_type="phishing",
            severity="high",
            pattern_data={},
            sample_size=10,
            confidence=0.7,
        )
        e2e_session.add(signal)
        await e2e_session.flush()
        await e2e_session.commit()

        resp = await intel_client.post(
            "/api/v1/intel-network/feedback",
            json={"signal_id": str(signal.id), "is_helpful": True, "notes": "Confirmed phishing"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "feedback_recorded"

    @pytest.mark.asyncio
    async def test_submit_false_positive_feedback(
        self, intel_client: AsyncClient, e2e_session
    ):
        signal = ThreatSignal(
            id=uuid.uuid4(),
            signal_type="spam",
            severity="low",
            pattern_data={},
            sample_size=5,
            confidence=0.3,
        )
        e2e_session.add(signal)
        await e2e_session.flush()
        await e2e_session.commit()

        resp = await intel_client.post(
            "/api/v1/intel-network/feedback",
            json={"signal_id": str(signal.id), "is_helpful": False},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_feedback_nonexistent_signal_returns_404(self, intel_client: AsyncClient):
        resp = await intel_client.post(
            "/api/v1/intel-network/feedback",
            json={"signal_id": str(uuid.uuid4()), "is_helpful": True},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_subscribe_contribute_fetch_feedback_unsubscribe(
        self, intel_client: AsyncClient, e2e_session
    ):
        # 1. Subscribe
        sub_resp = await intel_client.post(
            "/api/v1/intel-network/subscribe",
            json={"minimum_severity": "low"},
        )
        assert sub_resp.status_code == 201

        # 2. Contribute a signal
        contrib_resp = await intel_client.post(
            "/api/v1/intel-network/contribute",
            json={
                "signal_type": "emotional_dependency",
                "severity": "medium",
                "pattern_data": {"platform": "character_ai", "sessions_per_day": 15},
            },
        )
        assert contrib_resp.status_code == 201
        signal_id = contrib_resp.json()["id"]

        # 3. Boost sample_size so it shows in feed (k-anonymity threshold)
        from sqlalchemy import update as sa_update
        await e2e_session.execute(
            sa_update(ThreatSignal)
            .where(ThreatSignal.id == uuid.UUID(signal_id))
            .values(sample_size=10)
        )
        await e2e_session.commit()

        # 4. Fetch feed
        feed_resp = await intel_client.get("/api/v1/intel-network/feed")
        assert feed_resp.status_code == 200
        assert any(s["id"] == signal_id for s in feed_resp.json())

        # 5. Submit feedback
        fb_resp = await intel_client.post(
            "/api/v1/intel-network/feedback",
            json={"signal_id": signal_id, "is_helpful": True, "notes": "Confirmed pattern"},
        )
        assert fb_resp.status_code == 200

        # 6. Unsubscribe
        unsub_resp = await intel_client.delete("/api/v1/intel-network/subscribe")
        assert unsub_resp.status_code == 204

        # 7. Feed should now 404
        feed_resp2 = await intel_client.get("/api/v1/intel-network/feed")
        assert feed_resp2.status_code == 404
