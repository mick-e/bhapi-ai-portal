"""Database connection and session management."""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, with_loader_criteria

from src.config import get_settings

logger = structlog.get_logger()

settings = get_settings()

# Build engine kwargs based on database type
_engine_kwargs: dict = {
    "echo": settings.is_development,
}

if "sqlite" in settings.database_url:
    # SQLite: use StaticPool for in-memory DBs, no pool_size/max_overflow
    from sqlalchemy.pool import StaticPool
    _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: connection pool settings (configurable per service)
    pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    _engine_kwargs["pool_size"] = pool_size
    _engine_kwargs["max_overflow"] = pool_size // 2  # 50% of pool_size
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 3600

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass


# Soft-delete auto-filter: appends WHERE deleted_at IS NULL to all ORM SELECTs.
# Bypass with: session.execute(select(Model).execution_options(include_deleted=True))
@event.listens_for(Session, "do_orm_execute")
def _apply_soft_delete_filter(execute_state):
    """Auto-filter soft-deleted records on every ORM SELECT."""
    if (
        execute_state.is_select
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        from src.models import SoftDeleteMixin

        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of request context."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(max_retries: int = 10, retry_delay: float = 1.0) -> None:
    """Initialize database tables with retry logic."""
    last_error = None
    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_connected", attempt=attempt + 1)
            return
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning("database_connection_retry", attempt=attempt + 1, error=str(e))
                await asyncio.sleep(retry_delay)
            else:
                logger.error("database_connection_failed", attempts=max_retries, error=str(e))
    if last_error:
        raise last_error


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
