"""E2E tests for SSE (Server-Sent Events) real-time alert streaming.

Tests cover:
- SSEConnectionManager connect/disconnect/broadcast logic
- SSE stream endpoint requires group_id
- Alert creation triggers SSE broadcast
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.alerts.schemas import AlertCreate
from src.alerts.sse import SSEConnectionManager
from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Fixture — committing session (same pattern as test_risk_alerts.py)
# ---------------------------------------------------------------------------

@pytest.fixture
async def sse_client():
    """Test client with committing DB session for SSE tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, session

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# SSEConnectionManager unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse_manager_connect_disconnect():
    """connect() returns a queue, disconnect() removes it."""
    manager = SSEConnectionManager()
    gid = uuid4()

    queue = manager.connect(gid)
    assert gid in manager._connections
    assert len(manager._connections[gid]) == 1
    assert manager.connection_count == 1

    manager.disconnect(gid, queue)
    assert gid not in manager._connections
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_sse_manager_broadcast():
    """broadcast() sends a message to all listeners and returns count."""
    manager = SSEConnectionManager()
    gid = uuid4()

    q1 = manager.connect(gid)
    q2 = manager.connect(gid)

    count = await manager.broadcast(gid, "new_alert", {"id": "test-123", "severity": "high"})
    assert count == 2

    msg1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    msg2 = await asyncio.wait_for(q2.get(), timeout=1.0)

    # Messages are pre-formatted SSE strings
    assert "event: new_alert" in msg1
    assert '"id": "test-123"' in msg1
    assert msg1 == msg2

    manager.disconnect(gid, q1)
    manager.disconnect(gid, q2)


@pytest.mark.asyncio
async def test_sse_manager_broadcast_no_listeners():
    """broadcast() to a group with no listeners returns 0."""
    manager = SSEConnectionManager()
    gid = uuid4()

    count = await manager.broadcast(gid, "new_alert", {"id": "test"})
    assert count == 0


@pytest.mark.asyncio
async def test_sse_stream_endpoint_requires_group_id(sse_client):
    """GET /alerts/stream without group_id returns 422."""
    client, _ = sse_client
    # Register and login to get a valid token
    reg = await client.post("/api/v1/auth/register", json={
        "email": "sse-422@example.com",
        "password": "SecurePass1",
        "display_name": "SSE 422 Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    resp = await client.get(
        "/api/v1/alerts/stream",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_alert_creation_triggers_sse(sse_client):
    """Creating an alert via the service broadcasts to SSE manager."""
    client, session = sse_client

    # Register a user to get a valid group
    reg = await client.post("/api/v1/auth/register", json={
        "email": "sse-trigger@example.com",
        "password": "SecurePass1",
        "display_name": "SSE Trigger Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_data = me.json()
    group_id = user_data.get("group_id")

    if not group_id:
        pytest.skip("User registration did not create a group")

    from src.alerts.sse import sse_manager

    with patch.object(sse_manager, "broadcast", new_callable=AsyncMock, return_value=1) as mock_broadcast:
        from src.alerts.service import create_alert

        alert_data = AlertCreate(
            group_id=group_id,
            severity="high",
            title="Test SSE Alert",
            body="This alert should trigger an SSE broadcast",
            channel="portal",
        )
        await create_alert(session, alert_data)

        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert str(call_args[0][0]) == group_id  # group_id
        assert call_args[0][1] == "new_alert"  # event_type
        assert call_args[0][2]["severity"] == "high"  # data dict
