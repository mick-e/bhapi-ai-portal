"""Ohio governance extensions — district customization, import log.

Revision ID: 035
Revises: 033
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa
from migration_helpers import table_exists

revision = "035"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add district columns to governance_policies
    with op.batch_alter_table("governance_policies") as batch_op:
        batch_op.add_column(
            sa.Column("district_name", sa.String(200), nullable=True),
        )
        batch_op.add_column(
            sa.Column("district_customizations", sa.JSON(), nullable=True),
        )

    # Create governance_import_logs table
    if not table_exists("governance_import_logs"):
        op.create_table(
            "governance_import_logs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "school_id", sa.Uuid(),
                sa.ForeignKey("groups.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("import_type", sa.String(30), nullable=False),  # csv, json
            sa.Column("total_rows", sa.Integer(), nullable=False, default=0),
            sa.Column("imported_count", sa.Integer(), nullable=False, default=0),
            sa.Column("error_count", sa.Integer(), nullable=False, default=0),
            sa.Column("errors", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("governance_import_logs")
    with op.batch_alter_table("governance_policies") as batch_op:
        batch_op.drop_column("district_customizations")
        batch_op.drop_column("district_name")
