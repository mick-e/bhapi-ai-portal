"""SOC 2 audit tables: audit_policies, evidence_collections, compliance_controls.

Revision ID: 052
Revises: 051
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_policies_category", "audit_policies", ["category"])

    op.create_table(
        "evidence_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_policies.id"),
            nullable=True,
        ),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_collections_evidence_type",
        "evidence_collections",
        ["evidence_type"],
    )

    op.create_table(
        "compliance_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("control_id", sa.String(20), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("evidence_ids", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_compliance_controls_control_id",
        "compliance_controls",
        ["control_id"],
        unique=True,
    )
    op.create_index(
        "ix_compliance_controls_status",
        "compliance_controls",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_controls_status", table_name="compliance_controls")
    op.drop_index("ix_compliance_controls_control_id", table_name="compliance_controls")
    op.drop_table("compliance_controls")

    op.drop_index(
        "ix_evidence_collections_evidence_type", table_name="evidence_collections"
    )
    op.drop_table("evidence_collections")

    op.drop_index("ix_audit_policies_category", table_name="audit_policies")
    op.drop_table("audit_policies")
