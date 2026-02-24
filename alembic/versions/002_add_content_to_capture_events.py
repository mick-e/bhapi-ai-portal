"""Add content column to capture_events.

Revision ID: 002
Revises: 001
Create Date: 2026-02-23

The risk pipeline needs text content to classify, but capture_events
only stored metadata.  This adds a nullable TEXT column for the actual
prompt/response content.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("capture_events", sa.Column("content", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("capture_events", "content")
