"""Pytest fixtures for Bhapi AI Portal tests."""

import os as _os

_os.environ.setdefault("RATE_LIMIT_FAIL_OPEN", "true")
_os.environ.setdefault("ENVIRONMENT", "test")
_os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
_os.environ.setdefault("REDIS_URL", "")
_os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-min32chars")

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.api_platform.models  # noqa: F401

# Import all models so Base.metadata.create_all creates every table.
# Without this, lazily-imported models (e.g. AuditLog) won't have their
# tables created, causing "no such table" errors in tests.
import src.auth.models  # noqa: F401
import src.compliance.audit_logger  # noqa: F401
import src.creative.models  # noqa: F401
import src.groups.models  # noqa: F401
import src.intelligence.models  # noqa: F401
import src.location.models  # noqa: F401
import src.screen_time.models  # noqa: F401
from src.database import Base, get_db
from src.main import create_app
from src.middleware.rate_limit import _endpoint_limiter


async def make_test_group(session, name="Test", group_type="family", **kwargs):
    """Create a Group with a real User to satisfy FK constraints.

    Returns (group, owner_id). Use this in tests instead of creating
    Group(owner_id=uuid4()) which fails FK checks.
    """
    from uuid import uuid4

    from src.auth.models import User
    from src.groups.models import Group

    owner_id = kwargs.pop("owner_id", None) or uuid4()
    user = User(
        id=owner_id,
        email=f"test-{uuid4().hex[:8]}@example.com",
        display_name="Test User",
        account_type=group_type,
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(
        id=kwargs.pop("id", None) or uuid4(),
        name=name,
        type=group_type,
        owner_id=owner_id,
        settings=kwargs.pop("settings", {}),
        **kwargs,
    )
    session.add(group)
    await session.flush()
    return group, owner_id

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _clear_endpoint_rate_limiter():
    """Reset per-endpoint rate limiter between tests.

    Without this, the in-memory rate limiter accumulates hits across test
    functions (all from 127.0.0.1), causing registration to return 429
    after ~5 tests and cascading KeyError: 'access_token' failures.
    """
    _endpoint_limiter._buckets.clear()
    yield
    _endpoint_limiter._buckets.clear()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        # Disable FK constraints before dropping to avoid circular-FK errors
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def authed_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with auth headers.

    Uses a dummy Bearer token so auth middleware doesn't block requests.
    For tests that need real auth, override get_current_user dependency.
    """
    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac
