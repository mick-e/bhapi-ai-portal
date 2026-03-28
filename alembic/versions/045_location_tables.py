"""Create location tables — records, geofences, school check-in, privacy controls.

Revision ID: 045
Revises: 044
Create Date: 2026-03-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from migration_helpers import table_exists

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # location_records — encrypted lat/lng data points from device agent
    if not table_exists("location_records"):
        op.create_table(
            "location_records",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("latitude", sa.String(255), nullable=False),   # encrypted
            sa.Column("longitude", sa.String(255), nullable=False),  # encrypted
            sa.Column("accuracy", sa.Float(), nullable=False),
            sa.Column("source", sa.String(20), nullable=False, server_default="gps"),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_location_records_member_id", "location_records", ["member_id"])
        op.create_index("ix_location_records_group_id", "location_records", ["group_id"])
        op.create_index("ix_location_records_member_recorded", "location_records", ["member_id", "recorded_at"])

    # geofences — parent-defined boundaries
    if not table_exists("geofences"):
        op.create_table(
            "geofences",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("radius_meters", sa.Float(), nullable=False),
            sa.Column("notify_on_enter", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notify_on_exit", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_geofences_group_member", "geofences", ["group_id", "member_id"])

    # geofence_events — enter/exit event log
    if not table_exists("geofence_events"):
        op.create_table(
            "geofence_events",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("geofence_id", sa.Uuid(), sa.ForeignKey("geofences.id", ondelete="CASCADE"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(10), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_geofence_events_geofence_id", "geofence_events", ["geofence_id"])
        op.create_index("ix_geofence_events_geofence_recorded", "geofence_events", ["geofence_id", "recorded_at"])

    # school_checkins — attendance records (school sees check-in time only, never coordinates)
    if not table_exists("school_checkins"):
        op.create_table(
            "school_checkins",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("geofence_id", sa.Uuid(), sa.ForeignKey("geofences.id", ondelete="CASCADE"), nullable=False),
            sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_school_checkins_member_id", "school_checkins", ["member_id"])
        op.create_index("ix_school_checkins_member_date", "school_checkins", ["member_id", "check_in_at"])

    # location_sharing_consents — parental consent for school location sharing
    if not table_exists("location_sharing_consents"):
        op.create_table(
            "location_sharing_consents",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(
            "ix_location_consent_member_group",
            "location_sharing_consents",
            ["member_id", "group_id"],
            unique=True,
        )

    # location_kill_switches — parent-controlled emergency stop
    if not table_exists("location_kill_switches"):
        op.create_table(
            "location_kill_switches",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("activated_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # location_audit_logs — every access to location data is logged
    if not table_exists("location_audit_logs"):
        op.create_table(
            "location_audit_logs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("accessor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("data_type", sa.String(20), nullable=False),
            sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_location_audit_member_id", "location_audit_logs", ["member_id"])
        op.create_index("ix_location_audit_member_accessed", "location_audit_logs", ["member_id", "accessed_at"])


def downgrade() -> None:
    op.drop_table("location_audit_logs")
    op.drop_table("location_kill_switches")
    op.drop_table("location_sharing_consents")
    op.drop_table("school_checkins")
    op.drop_table("geofence_events")
    op.drop_table("geofences")
    op.drop_table("location_records")
