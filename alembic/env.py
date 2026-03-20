"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config import get_settings
from src.database import Base

# Import ALL models so they register with Base.metadata
from src.auth.models import User, OAuthConnection, ApiKey, Session  # noqa: F401
from src.groups.models import Group, GroupMember, Invitation, ClassGroup, ClassGroupMember  # noqa: F401
from src.groups.agreement import FamilyAgreement  # noqa: F401
from src.groups.emergency_contacts import EmergencyContact  # noqa: F401
from src.groups.privacy import MemberVisibility, ChildSelfView  # noqa: F401
from src.groups.rewards import Reward  # noqa: F401
from src.capture.models import CaptureEvent, DeviceRegistration, SetupCode  # noqa: F401
from src.capture.summary_models import ConversationSummary  # noqa: F401
from src.risk.models import RiskEvent, RiskConfig, ContentExcerpt  # noqa: F401
from src.alerts.models import Alert, NotificationPreference  # noqa: F401
from src.alerts.panic import PanicReport  # noqa: F401
from src.billing.models import Subscription, LLMAccount, SpendRecord, BudgetThreshold, FiredThresholdAlert  # noqa: F401
from src.reporting.models import ScheduledReport, ReportExport  # noqa: F401
from src.compliance.models import ConsentRecord, DataDeletionRequest, AuditEntry, ThirdPartyConsentItem, RetentionPolicy, PushNotificationConsent, VideoVerification  # noqa: F401
from src.compliance.eu_ai_act_models import HumanReviewRequest, AppealRecord  # noqa: F401
from src.blocking.models import BlockRule, AutoBlockRule  # noqa: F401
from src.blocking.approval_models import BlockApproval  # noqa: F401
from src.blocking.time_budget import TimeBudget, TimeBudgetUsage  # noqa: F401
from src.integrations.models import SISConnection  # noqa: F401
from src.integrations.sso_models import SSOConfig  # noqa: F401
from src.literacy.models import LiteracyModule, LiteracyQuestion, LiteracyAssessment, LiteracyProgress  # noqa: F401
from src.portal.demo import DemoSession  # noqa: F401
from src.portal.onboarding import OnboardingProgress  # noqa: F401
from src.alerts.web_push import PushSubscription  # noqa: F401
from src.alerts.escalation import EscalationPartner, EscalationRecord  # noqa: F401
from src.groups.district import District, DistrictSchool  # noqa: F401
from src.groups.teacher_dashboard import ParentTeacherNote  # noqa: F401
from src.compliance.audit_logger import AuditLog  # noqa: F401
from src.compliance.incident import IncidentRecord  # noqa: F401
from src.integrations.cross_product import ProductRegistration, SharedProfile, CrossProductAlert  # noqa: F401
from src.integrations.developer_portal import DeveloperApp, WebhookEndpoint, WebhookDelivery, MarketplaceModule, InstalledModule  # noqa: F401
from src.risk.enterprise_policy import AIUsagePolicy, PolicyViolation  # noqa: F401
from src.blocking.url_filter import URLFilterRule, URLCategory  # noqa: F401
from src.alerts.correlation import AlertCorrelation  # noqa: F401
from src.age_tier.models import AgeTierConfig  # noqa: F401
from src.social.models import Profile, SocialPost, PostComment, PostLike, Hashtag, PostHashtag, Follow  # noqa: F401
from src.contacts.models import Contact, ContactApproval  # noqa: F401
from src.moderation.models import ModerationQueue, ModerationDecision, ContentReport, MediaAsset  # noqa: F401
from src.governance.models import GovernancePolicy, GovernanceAudit, GovernanceImportLog  # noqa: F401
from src.messaging.models import Conversation, ConversationMember, Message, MessageMedia  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment if available
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
