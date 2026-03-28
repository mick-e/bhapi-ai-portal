"""Shared fixtures for security tests.

Provides common setup patterns used across many security test files.
Individual test files that define their own local fixtures (e.g. a local
``sec_client``) will continue to use those — pytest scoping rules give
local fixtures priority over conftest-level ones.
"""

from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.models import User
from src.auth.service import create_access_token
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Engine & session fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sec_engine():
    """In-memory SQLite async engine for security tests.

    Creates all tables on startup, drops them on teardown.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
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

    yield engine

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def sec_session(sec_engine):
    """Async session bound to ``sec_engine``.

    Uses a sessionmaker so each test gets a fresh session object.
    """
    maker = sessionmaker(sec_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sec_client(sec_engine):
    """AsyncClient wired to a FastAPI app that commits after each request.

    Yields ``(client, session)`` — many security tests need both to seed
    data and then hit endpoints.
    """
    session = AsyncSession(sec_engine, expire_on_commit=False)
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


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def auth_header_for_user(user: User) -> dict[str, str]:
    """Generate a valid JWT Bearer header for the given user.

    The token has ``type: "session"`` so it passes the auth middleware's
    token-type check.
    """
    token = create_access_token(
        {"sub": str(user.id), "type": "session"},
    )
    return {"Authorization": f"Bearer {token}"}


async def register_and_get_auth(
    client: AsyncClient,
    email: str,
    *,
    password: str = "SecurePass1!",
    display_name: str = "User",
    account_type: str = "family",
) -> tuple[dict[str, str], str | None, str]:
    """Register a user via the API and return ``(headers, group_id, user_id)``.

    This is the pattern used by IDOR / cross-group tests that register two
    users and then have one attempt to access the other's resources.
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "account_type": account_type,
            "privacy_notice_accepted": True,
        },
    )
    token = reg.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    me_data = me.json()
    return headers, me_data.get("group_id"), me_data["id"]


# ---------------------------------------------------------------------------
# Data-seeding helpers
# ---------------------------------------------------------------------------


async def make_two_users_different_groups(
    session: AsyncSession,
    *,
    account_type: str = "family",
) -> tuple[tuple[User, Group], tuple[User, Group]]:
    """Create two users, each owning a separate group.

    Returns ``((user_a, group_a), (user_b, group_b))``.
    Useful for IDOR / data-isolation tests that need two independent
    principals.
    """
    user_a = User(
        id=uuid4(),
        email=f"user-a-{uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="User A",
        account_type=account_type,
        email_verified=False,
        mfa_enabled=False,
    )
    user_b = User(
        id=uuid4(),
        email=f"user-b-{uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="User B",
        account_type=account_type,
        email_verified=False,
        mfa_enabled=False,
    )
    session.add_all([user_a, user_b])
    await session.flush()

    group_a = Group(
        id=uuid4(),
        name="Group A",
        type=account_type,
        owner_id=user_a.id,
        settings={},
    )
    group_b = Group(
        id=uuid4(),
        name="Group B",
        type=account_type,
        owner_id=user_b.id,
        settings={},
    )
    session.add_all([group_a, group_b])
    await session.flush()

    return (user_a, group_a), (user_b, group_b)
