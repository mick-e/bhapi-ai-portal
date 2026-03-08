"""Unit tests for export file auto-deletion."""

import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_cleanup_deletes_old_files(test_session):
    """Files older than 7 days should be deleted."""
    from src.compliance.file_cleanup import cleanup_expired_exports

    with tempfile.TemporaryDirectory() as tmpdir:
        exports_dir = Path(tmpdir)

        # Create an old file (mtime = 10 days ago)
        old_file = exports_dir / "old_export.zip"
        old_file.write_bytes(b"old data")
        old_mtime = time.time() - (10 * 86400)
        os.utime(old_file, (old_mtime, old_mtime))

        # Create a recent file
        new_file = exports_dir / "new_export.zip"
        new_file.write_bytes(b"new data")

        with patch("src.compliance.file_cleanup.EXPORTS_DIR", exports_dir):
            deleted = await cleanup_expired_exports(test_session)

        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()


@pytest.mark.asyncio
async def test_cleanup_no_exports_dir(test_session):
    """Cleanup should return 0 if exports dir doesn't exist."""
    from src.compliance.file_cleanup import cleanup_expired_exports

    with patch("src.compliance.file_cleanup.EXPORTS_DIR", Path("/nonexistent")):
        deleted = await cleanup_expired_exports(test_session)
    assert deleted == 0
