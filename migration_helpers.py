"""Helpers for making Alembic migrations idempotent.

These guard functions allow migrations to run safely even when
database objects already exist (e.g. after a manual schema change
or a stale alembic_version stamp).
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect


def table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return inspector.has_table(table_name)


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column already exists on a table."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if not inspector.has_table(table_name):
        return False
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index already exists on a table."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if not inspector.has_table(table_name):
        return False
    indexes = [i["name"] for i in inspector.get_indexes(table_name)]
    return index_name in indexes
