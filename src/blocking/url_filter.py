"""URL content filtering for broader web safety."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, String, DateTime, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()

# Default URL categories
URL_CATEGORIES = [
    {"key": "adult", "name": "Adult Content", "description": "Pornography and sexually explicit material"},
    {"key": "violence", "name": "Violence", "description": "Graphic violence, gore, and weapons"},
    {"key": "gambling", "name": "Gambling", "description": "Online gambling and betting sites"},
    {"key": "drugs", "name": "Drugs & Alcohol", "description": "Drug-related content and substance abuse"},
    {"key": "social_media", "name": "Social Media", "description": "Social networking platforms"},
    {"key": "gaming", "name": "Gaming", "description": "Online games and gaming platforms"},
    {"key": "streaming", "name": "Streaming", "description": "Video streaming and entertainment"},
    {"key": "malware", "name": "Malware & Phishing", "description": "Known malicious websites"},
    {"key": "hate_speech", "name": "Hate Speech", "description": "Hate groups and extremist content"},
    {"key": "self_harm", "name": "Self-Harm", "description": "Self-harm and suicide content"},
]


class URLFilterRule(Base, UUIDMixin, TimestampMixin):
    """A URL filtering rule for a group."""

    __tablename__ = "url_filter_rules"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="block")  # block, warn, log
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class URLCategory(Base, UUIDMixin, TimestampMixin):
    """Custom URL category for a group."""

    __tablename__ = "url_categories"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_patterns: Mapped[list | None] = mapped_column(JSONType, nullable=True)


def get_default_categories() -> list[dict]:
    """Get default URL filter categories."""
    return URL_CATEGORIES


async def create_filter_rule(
    db: AsyncSession,
    group_id: uuid.UUID,
    category: str,
    action: str = "block",
    member_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
) -> URLFilterRule:
    """Create a URL filter rule."""
    if action not in ("block", "warn", "log"):
        raise ValidationError("Action must be block, warn, or log")

    rule = URLFilterRule(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        category=category,
        action=action,
        active=True,
        created_by=created_by or uuid.uuid4(),
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info("url_filter_created", category=category, action=action)
    return rule


async def list_filter_rules(
    db: AsyncSession, group_id: uuid.UUID
) -> list[URLFilterRule]:
    """List URL filter rules for a group."""
    result = await db.execute(
        select(URLFilterRule).where(
            URLFilterRule.group_id == group_id,
            URLFilterRule.active.is_(True),
        )
    )
    return list(result.scalars().all())


async def check_url(
    db: AsyncSession, group_id: uuid.UUID, url: str, member_id: uuid.UUID | None = None
) -> dict:
    """Check if a URL should be filtered."""
    rules = await list_filter_rules(db, group_id)
    # Simple domain-based categorization (in production, use a classification service)
    blocked_categories = []
    for rule in rules:
        if member_id and rule.member_id and rule.member_id != member_id:
            continue
        blocked_categories.append({"category": rule.category, "action": rule.action})

    return {
        "url": url,
        "allowed": len(blocked_categories) == 0,
        "matching_rules": blocked_categories,
    }
