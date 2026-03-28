"""Create creative tables — AI art, stories, stickers, drawings.

Revision ID: 047
Revises: 046
Create Date: 2026-03-24
"""

import sqlalchemy as sa
from alembic import op
from migration_helpers import table_exists

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # art_generations — AI-generated images from member prompts
    if not table_exists("art_generations"):
        op.create_table(
            "art_generations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("sanitized_prompt", sa.Text(), nullable=False),
            sa.Column("model", sa.String(30), nullable=False, server_default="dalle3"),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_art_generations_member_id", "art_generations", ["member_id"])
        op.create_index("ix_art_generations_group_id", "art_generations", ["group_id"])
        op.create_index("ix_art_generations_member_moderation", "art_generations", ["member_id", "moderation_status"])

    # story_templates — curated templates for guided writing
    if not table_exists("story_templates"):
        op.create_table(
            "story_templates",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("theme", sa.String(30), nullable=False),
            sa.Column("content_template", sa.Text(), nullable=False),
            sa.Column("min_age_tier", sa.String(20), nullable=False),
            sa.Column("template_type", sa.String(30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # story_creations — member-written stories (optional template)
    if not table_exists("story_creations"):
        op.create_table(
            "story_creations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("template_id", sa.Uuid(), sa.ForeignKey("story_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("posted_to_feed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_story_creations_member_id", "story_creations", ["member_id"])
        op.create_index("ix_story_creations_template_id", "story_creations", ["template_id"])
        op.create_index("ix_story_creations_member_moderation", "story_creations", ["member_id", "moderation_status"])

    # sticker_packs — grouped sticker collections
    if not table_exists("sticker_packs"):
        op.create_table(
            "sticker_packs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("category", sa.String(30), nullable=False),
            sa.Column("is_curated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # stickers — individual sticker images (curated or user-created)
    if not table_exists("stickers"):
        op.create_table(
            "stickers",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("pack_id", sa.Uuid(), sa.ForeignKey("sticker_packs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="SET NULL"), nullable=True),
            sa.Column("image_url", sa.String(500), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_stickers_pack_id", "stickers", ["pack_id"])
        op.create_index("ix_stickers_member_id", "stickers", ["member_id"])

    # drawing_assets — freehand member drawings
    if not table_exists("drawing_assets"):
        op.create_table(
            "drawing_assets",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("member_id", sa.Uuid(), sa.ForeignKey("group_members.id", ondelete="CASCADE"), nullable=False),
            sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=False),
            sa.Column("moderation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("posted_to_feed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_drawing_assets_member_id", "drawing_assets", ["member_id"])
        op.create_index("ix_drawing_assets_group_id", "drawing_assets", ["group_id"])
        op.create_index("ix_drawing_assets_member_moderation", "drawing_assets", ["member_id", "moderation_status"])


def downgrade() -> None:
    op.drop_table("drawing_assets")
    op.drop_table("stickers")
    op.drop_table("sticker_packs")
    op.drop_table("story_creations")
    op.drop_table("story_templates")
    op.drop_table("art_generations")
