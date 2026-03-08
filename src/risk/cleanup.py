"""Content excerpt TTL cleanup — deletes expired content excerpts."""

from datetime import datetime, timezone

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.risk.models import ContentExcerpt

logger = structlog.get_logger()


async def cleanup_expired_excerpts(db: AsyncSession) -> int:
    """Delete content excerpts that have passed their expiry date."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(ContentExcerpt).where(ContentExcerpt.expires_at < now)
    )
    count = result.rowcount
    await db.flush()
    logger.info("excerpt_cleanup_completed", deleted=count)
    return count
