"""Compliance database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin

# ---------------------------------------------------------------------------
# SOC 2 — Audit policies, evidence collection, compliance controls
# ---------------------------------------------------------------------------


class AuditPolicy(Base, UUIDMixin, TimestampMixin):
    """SOC 2 audit policy document record.

    Tracks formal policy documents mapped to Trust Services Criteria categories.
    Each policy covers a specific area of security, availability, or privacy.
    """

    __tablename__ = "audit_policies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # security / availability / confidentiality / privacy
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    effective_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EvidenceCollection(Base, UUIDMixin, TimestampMixin):
    """SOC 2 evidence artifact collected during audit preparation.

    Stores deployment logs, access-control snapshots, encryption status records,
    backup verifications, and incident timelines as JSON blobs.
    """

    __tablename__ = "evidence_collections"

    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_policies.id"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # deployment_log / access_control / encryption / backup / incident
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)


class ComplianceControl(Base, UUIDMixin, TimestampMixin):
    """SOC 2 Trust Services Criteria control mapping.

    Maps individual controls (e.g. CC6.1) to implementation status and
    evidence artifact IDs collected for the auditor.
    """

    __tablename__ = "compliance_controls"

    control_id: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )  # e.g. "CC6.1"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned"
    )  # implemented / partial / planned
    evidence_ids: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )  # list of EvidenceCollection UUIDs


class ConsentRecord(Base, UUIDMixin, TimestampMixin):
    """Record of consent given or withdrawn (GDPR, COPPA, LGPD)."""

    __tablename__ = "consent_records"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # monitoring, data_collection, ai_interaction, marketing
    parent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )  # IPv4 or IPv6
    evidence: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )  # Signed consent form reference, checkbox ID, etc.
    region_specific_consent: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True
    )  # Per-region consent metadata (UK AADC, etc.)


class DataDeletionRequest(Base, UUIDMixin, TimestampMixin):
    """GDPR Article 17 / COPPA data deletion request."""

    __tablename__ = "data_deletion_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # full_deletion, data_export, rectification
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditEntry(Base, UUIDMixin):
    """Immutable audit log entry for compliance tracking."""

    __tablename__ = "audit_entries"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., consent.granted, data.exported, member.added
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # user, group, member, consent, alert
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# COPPA 2026 — Third-party data flow consent
# ---------------------------------------------------------------------------


class ThirdPartyConsentItem(Base, UUIDMixin, TimestampMixin):
    """Per-third-party consent toggle (COPPA 2026 granular consent).

    Each row represents a parent's consent decision for a specific third-party
    provider (e.g., Stripe, SendGrid, Google Cloud AI, Hive/Sensity).
    """

    __tablename__ = "third_party_consent_items"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    provider_key: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # stripe, sendgrid, twilio, google_cloud_ai, hive_sensity
    provider_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Human-readable name
    data_purpose: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # What data is shared and why
    consented: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )


# ---------------------------------------------------------------------------
# COPPA 2026 — Data retention policies
# ---------------------------------------------------------------------------


class RetentionPolicy(Base, UUIDMixin, TimestampMixin):
    """Configurable data retention policy per data type.

    Defines how long each category of child data is kept before automatic
    deletion. Parents can view these via the privacy settings page.
    """

    __tablename__ = "retention_policies"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    data_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # capture_events, risk_events, content_excerpts, conversation_summaries, alerts
    retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=365
    )
    description: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    auto_delete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_cleanup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    records_deleted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )


# ---------------------------------------------------------------------------
# COPPA 2026 — Push notification consent
# ---------------------------------------------------------------------------


class PushNotificationConsent(Base, UUIDMixin, TimestampMixin):
    """Separate consent for push notifications containing child data.

    COPPA 2026 requires explicit, separate consent before sending push
    notifications that contain information about a child's activity.
    """

    __tablename__ = "push_notification_consents"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # risk_alerts, activity_summaries, weekly_reports, all
    consented: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------------------------------------------------------------------------
# COPPA 2026 — Enhanced verifiable parental consent (video verification)
# ---------------------------------------------------------------------------


class VideoVerification(Base, UUIDMixin, TimestampMixin):
    """Video-based parental identity verification for enhanced VPC.

    Replaces knowledge-based-only consent with video verification as
    required by COPPA 2026 updates. Integrates with Yoti for identity.
    """

    __tablename__ = "video_verifications"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    verification_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # video_call, yoti_id_check, video_selfie
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, in_progress, verified, failed, expired
    yoti_session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    verification_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0.0-1.0 confidence score
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
