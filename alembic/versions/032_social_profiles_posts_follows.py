"""Social profiles, posts, follows, contacts, moderation, governance, messaging.

Revision ID: 032
Revises: 031
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_helpers import table_exists

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Social module ---
    if not table_exists("profiles"):
        op.create_table(
            "profiles",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=False),
            sa.Column("avatar_url", sa.String(1024), nullable=True),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("age_tier", sa.String(20), nullable=False),
            sa.Column("date_of_birth", sa.Date(), nullable=False),
            sa.Column("visibility", sa.String(20), nullable=False, server_default="friends_only"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_profiles_user_id"),
        )
        op.create_index("ix_profiles_user_id", "profiles", ["user_id"])

    if not table_exists("social_posts"):
        op.create_table(
            "social_posts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("author_id", sa.Uuid(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("post_type", sa.String(20), nullable=False, server_default="text"),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_social_posts_author_id", "social_posts", ["author_id"])

    if not table_exists("post_comments"):
        op.create_table(
            "post_comments",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("post_id", sa.Uuid(), nullable=False),
            sa.Column("author_id", sa.Uuid(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["social_posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_post_comments_post_id", "post_comments", ["post_id"])
        op.create_index("ix_post_comments_author_id", "post_comments", ["author_id"])

    if not table_exists("post_likes"):
        op.create_table(
            "post_likes",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("post_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["social_posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
        )
        op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])
        op.create_index("ix_post_likes_user_id", "post_likes", ["user_id"])

    if not table_exists("hashtags"):
        op.create_table(
            "hashtags",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not table_exists("post_hashtags"):
        op.create_table(
            "post_hashtags",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("post_id", sa.Uuid(), nullable=False),
            sa.Column("hashtag_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["social_posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["hashtag_id"], ["hashtags.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_post_hashtags_post_id", "post_hashtags", ["post_id"])
        op.create_index("ix_post_hashtags_hashtag_id", "post_hashtags", ["hashtag_id"])

    if not table_exists("follows"):
        op.create_table(
            "follows",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("follower_id", sa.Uuid(), nullable=False),
            sa.Column("following_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["following_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("follower_id", "following_id", name="uq_follows_follower_following"),
        )
        op.create_index("ix_follows_follower_id", "follows", ["follower_id"])
        op.create_index("ix_follows_following_id", "follows", ["following_id"])

    # --- Contacts module ---
    if not table_exists("contacts"):
        op.create_table(
            "contacts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("requester_id", sa.Uuid(), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("parent_approval_status", sa.String(20), nullable=False, server_default="not_required"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["target_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("requester_id", "target_id", name="uq_contacts_requester_target"),
        )
        op.create_index("ix_contacts_requester_id", "contacts", ["requester_id"])
        op.create_index("ix_contacts_target_id", "contacts", ["target_id"])

    if not table_exists("contact_approvals"):
        op.create_table(
            "contact_approvals",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("contact_id", sa.Uuid(), nullable=False),
            sa.Column("parent_user_id", sa.Uuid(), nullable=False),
            sa.Column("decision", sa.String(20), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_contact_approvals_contact_id", "contact_approvals", ["contact_id"])
        op.create_index("ix_contact_approvals_parent_user_id", "contact_approvals", ["parent_user_id"])

    # --- Moderation module ---
    if not table_exists("moderation_queue"):
        op.create_table(
            "moderation_queue",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("content_type", sa.String(20), nullable=False),
            sa.Column("content_id", sa.Uuid(), nullable=False),
            sa.Column("pipeline", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("risk_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("age_tier", sa.String(20), nullable=True),
            sa.Column("assigned_to", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_moderation_queue_content_id", "moderation_queue", ["content_id"])

    if not table_exists("moderation_decisions"):
        op.create_table(
            "moderation_decisions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("queue_id", sa.Uuid(), nullable=False),
            sa.Column("moderator_id", sa.Uuid(), nullable=True),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["queue_id"], ["moderation_queue.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["moderator_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_moderation_decisions_queue_id", "moderation_decisions", ["queue_id"])

    if not table_exists("content_reports"):
        op.create_table(
            "content_reports",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("reporter_id", sa.Uuid(), nullable=False),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_content_reports_reporter_id", "content_reports", ["reporter_id"])
        op.create_index("ix_content_reports_target_id", "content_reports", ["target_id"])

    if not table_exists("media_assets"):
        op.create_table(
            "media_assets",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("cloudflare_r2_key", sa.String(1024), nullable=True),
            sa.Column("cloudflare_image_id", sa.String(255), nullable=True),
            sa.Column("cloudflare_stream_id", sa.String(255), nullable=True),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("variants", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("content_length", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_media_assets_owner_id", "media_assets", ["owner_id"])

    # --- Governance module ---
    if not table_exists("governance_policies"):
        op.create_table(
            "governance_policies",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=False),
            sa.Column("state_code", sa.String(2), nullable=False),
            sa.Column("policy_type", sa.String(30), nullable=False),
            sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["school_id"], ["groups.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_governance_policies_school_id", "governance_policies", ["school_id"])

    if not table_exists("governance_audits"):
        op.create_table(
            "governance_audits",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("policy_id", sa.Uuid(), nullable=False),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=False),
            sa.Column("diff", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["policy_id"], ["governance_policies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_governance_audits_policy_id", "governance_audits", ["policy_id"])
        op.create_index("ix_governance_audits_actor_id", "governance_audits", ["actor_id"])

    # --- Messaging module ---
    if not table_exists("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("type", sa.String(20), nullable=False),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_conversations_created_by", "conversations", ["created_by"])

    if not table_exists("conversation_members"):
        op.create_table(
            "conversation_members",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("conversation_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("role", sa.String(20), nullable=False, server_default="member"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_conversation_members_conversation_id", "conversation_members", ["conversation_id"])
        op.create_index("ix_conversation_members_user_id", "conversation_members", ["user_id"])

    if not table_exists("messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("conversation_id", sa.Uuid(), nullable=False),
            sa.Column("sender_id", sa.Uuid(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
        op.create_index("ix_messages_sender_id", "messages", ["sender_id"])

    if not table_exists("message_media"):
        op.create_table(
            "message_media",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("message_id", sa.Uuid(), nullable=False),
            sa.Column("cloudflare_id", sa.String(255), nullable=False),
            sa.Column("media_type", sa.String(20), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_message_media_message_id", "message_media", ["message_id"])


def downgrade() -> None:
    op.drop_table("message_media")
    op.drop_table("messages")
    op.drop_table("conversation_members")
    op.drop_table("conversations")
    op.drop_table("governance_audits")
    op.drop_table("governance_policies")
    op.drop_table("media_assets")
    op.drop_table("content_reports")
    op.drop_table("moderation_decisions")
    op.drop_table("moderation_queue")
    op.drop_table("contact_approvals")
    op.drop_table("contacts")
    op.drop_table("follows")
    op.drop_table("post_hashtags")
    op.drop_table("hashtags")
    op.drop_table("post_likes")
    op.drop_table("post_comments")
    op.drop_table("social_posts")
    op.drop_table("profiles")
