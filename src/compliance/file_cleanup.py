"""Export file cleanup — deletes export files older than 7 days."""

import time
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EXPORTS_DIR = Path("data/exports")
MAX_AGE_DAYS = 7


async def cleanup_expired_exports(db: AsyncSession) -> int:
    """Delete export files older than MAX_AGE_DAYS."""
    if not EXPORTS_DIR.is_dir():
        return 0

    cutoff = time.time() - (MAX_AGE_DAYS * 86400)
    deleted = 0

    for filepath in EXPORTS_DIR.iterdir():
        if filepath.is_file() and filepath.stat().st_mtime < cutoff:
            try:
                filepath.unlink()
                deleted += 1
            except OSError as exc:
                logger.error("export_cleanup_error", file=str(filepath), error=str(exc))

    logger.info("export_cleanup_completed", deleted=deleted)
    return deleted
