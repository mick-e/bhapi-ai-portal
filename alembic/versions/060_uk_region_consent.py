"""Add region_specific_consent to consent_records — UK AADC re-review.

Phase 4 Task 24 (P4-INT1).

Stores per-region consent metadata so AADC consent (and future regional
overlays — e.g. CCPA-CA, AU eSafety acknowledgements) can be audited
independently of the base GDPR/COPPA consent_type.

Revision ID: 060
Revises: 059
Create Date: 2026-04-18
"""
import sqlalchemy as sa
from alembic import op

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("consent_records")}
    if "region_specific_consent" not in columns:
        with op.batch_alter_table("consent_records") as batch_op:
            batch_op.add_column(
                sa.Column("region_specific_consent", sa.JSON, nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("consent_records")}
    if "region_specific_consent" in columns:
        with op.batch_alter_table("consent_records") as batch_op:
            batch_op.drop_column("region_specific_consent")
