"""Creative service — AI art generation, stories, stickers, and drawings."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import age_from_dob, get_tier_for_age
from src.creative.models import (
    ArtGeneration,
    DrawingAsset,
    Sticker,
    StickerPack,
    StoryCreation,
    StoryTemplate,
)
from src.exceptions import NotFoundError, RateLimitError, ValidationError
from src.groups.models import GroupMember

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Content moderation — keyword block list
# ---------------------------------------------------------------------------

_BLOCKED_KEYWORDS = {
    "nude", "nudity", "naked", "violence", "violent", "drugs", "drug",
    "weapons", "weapon", "blood", "kill", "kills", "killing", "killed",
    "sex", "sexual", "sexy", "porn", "pornography", "pornographic",
    "gun", "guns", "firearm",
}

# Daily art generation limits per age tier
_ART_RATE_LIMITS = {
    "young": 10,
    "preteen": 25,
    "teen": 50,
}
_DEFAULT_RATE_LIMIT = 10


def _sanitize_prompt(prompt: str) -> str:
    """Check prompt for blocked keywords. Raises ValidationError if found.

    Returns the stripped prompt if clean.
    """
    lower = prompt.lower()
    for word in _BLOCKED_KEYWORDS:
        # Match whole words only
        import re
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            raise ValidationError(
                f"Prompt contains inappropriate content. "
                f"Please use a different description."
            )
    return prompt.strip()


async def _get_member_age_tier(db: AsyncSession, member_id: UUID) -> str:
    """Look up age tier for a GroupMember via date_of_birth."""
    result = await db.execute(
        select(GroupMember).where(GroupMember.id == member_id)
    )
    member = result.scalar_one_or_none()
    if member is None or member.date_of_birth is None:
        return "young"  # default to most restrictive

    age = age_from_dob(member.date_of_birth)
    tier = get_tier_for_age(age)
    return tier.value if tier is not None else "young"


async def _count_art_today(db: AsyncSession, member_id: UUID) -> int:
    """Count ArtGeneration records created by member since start of UTC day."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    result = await db.execute(
        select(func.count()).where(
            and_(
                ArtGeneration.member_id == member_id,
                ArtGeneration.created_at >= today_start,
            )
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Art generation
# ---------------------------------------------------------------------------


async def generate_art(
    db: AsyncSession,
    member_id: UUID,
    group_id: UUID,
    prompt: str,
    model: str = "dalle3",
) -> ArtGeneration:
    """Sanitize prompt, enforce rate limit, create ArtGeneration record.

    Raises:
        ValidationError: Prompt contains blocked content.
        RateLimitError: Daily art generation limit exceeded for age tier.
    """
    sanitized = _sanitize_prompt(prompt)

    # Check rate limit
    age_tier = await _get_member_age_tier(db, member_id)
    daily_limit = _ART_RATE_LIMITS.get(age_tier, _DEFAULT_RATE_LIMIT)
    count_today = await _count_art_today(db, member_id)
    if count_today >= daily_limit:
        raise RateLimitError(
            f"Daily art generation limit of {daily_limit} reached for your age group. "
            f"Try again tomorrow."
        )

    art = ArtGeneration(
        member_id=member_id,
        group_id=group_id,
        prompt=prompt,
        sanitized_prompt=sanitized,
        model=model,
        moderation_status="pending",
    )
    db.add(art)
    await db.flush()
    logger.info("art_generated", member_id=str(member_id), group_id=str(group_id))
    return art


async def list_member_art(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[ArtGeneration]:
    """Return paginated ArtGeneration records for a member."""
    result = await db.execute(
        select(ArtGeneration)
        .where(ArtGeneration.member_id == member_id)
        .order_by(ArtGeneration.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Story templates
# ---------------------------------------------------------------------------


async def get_story_templates(
    db: AsyncSession,
    age_tier: str | None = None,
) -> list[StoryTemplate]:
    """Return all story templates, optionally filtered by min_age_tier."""
    query = select(StoryTemplate)
    if age_tier is not None:
        query = query.where(StoryTemplate.min_age_tier == age_tier)
    result = await db.execute(query.order_by(StoryTemplate.created_at.asc()))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Story creation
# ---------------------------------------------------------------------------


async def create_story(
    db: AsyncSession,
    member_id: UUID,
    content: str,
    template_id: UUID | None = None,
) -> StoryCreation:
    """Create a StoryCreation for a member.

    If template_id is provided, verifies the template exists.
    """
    if template_id is not None:
        tmpl_result = await db.execute(
            select(StoryTemplate).where(StoryTemplate.id == template_id)
        )
        if tmpl_result.scalar_one_or_none() is None:
            raise NotFoundError("StoryTemplate", str(template_id))

    story = StoryCreation(
        member_id=member_id,
        template_id=template_id,
        content=content,
        moderation_status="pending",
        posted_to_feed=False,
    )
    db.add(story)
    await db.flush()
    logger.info("story_created", member_id=str(member_id))
    return story


async def list_member_stories(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[StoryCreation]:
    """Return paginated StoryCreation records for a member."""
    result = await db.execute(
        select(StoryCreation)
        .where(StoryCreation.member_id == member_id)
        .order_by(StoryCreation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Drawings
# ---------------------------------------------------------------------------


async def save_drawing(
    db: AsyncSession,
    member_id: UUID,
    group_id: UUID,
    image_url: str,
) -> DrawingAsset:
    """Create a DrawingAsset for a member."""
    drawing = DrawingAsset(
        member_id=member_id,
        group_id=group_id,
        image_url=image_url,
        moderation_status="pending",
        posted_to_feed=False,
    )
    db.add(drawing)
    await db.flush()
    logger.info("drawing_saved", member_id=str(member_id), group_id=str(group_id))
    return drawing


async def list_member_drawings(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[DrawingAsset]:
    """Return paginated DrawingAsset records for a member."""
    result = await db.execute(
        select(DrawingAsset)
        .where(DrawingAsset.member_id == member_id)
        .order_by(DrawingAsset.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Stickers
# ---------------------------------------------------------------------------


async def _get_or_create_personal_pack(
    db: AsyncSession, member_id: UUID,
) -> StickerPack:
    """Get or create the personal StickerPack for a member."""
    result = await db.execute(
        select(StickerPack).where(
            and_(
                StickerPack.category == "user_created",
                StickerPack.is_curated == False,  # noqa: E712
                # Find packs that have at least one sticker for this member
                StickerPack.id.in_(
                    select(Sticker.pack_id).where(Sticker.member_id == member_id)
                ),
            )
        ).limit(1)
    )
    pack = result.scalar_one_or_none()
    if pack is None:
        # Also check if a user_created pack exists without stickers yet
        # (created previously for this member via name convention)
        name = f"personal_{member_id}"
        name_result = await db.execute(
            select(StickerPack).where(StickerPack.name == name).limit(1)
        )
        pack = name_result.scalar_one_or_none()

    if pack is None:
        pack = StickerPack(
            name=f"personal_{member_id}",
            category="user_created",
            is_curated=False,
        )
        db.add(pack)
        await db.flush()
        logger.info("sticker_pack_created", member_id=str(member_id))

    return pack


async def create_custom_sticker(
    db: AsyncSession,
    member_id: UUID,
    image_url: str,
) -> Sticker:
    """Create a Sticker in the member's personal pack (creating pack if needed)."""
    pack = await _get_or_create_personal_pack(db, member_id)
    sticker = Sticker(
        pack_id=pack.id,
        member_id=member_id,
        image_url=image_url,
        moderation_status="pending",
    )
    db.add(sticker)
    await db.flush()
    logger.info("sticker_created", member_id=str(member_id), pack_id=str(pack.id))
    return sticker


async def get_sticker_packs(
    db: AsyncSession,
    include_user_packs: bool = False,
    member_id: UUID | None = None,
) -> list[StickerPack]:
    """List curated sticker packs. Optionally include user packs.

    When include_user_packs=True and member_id is provided, also return
    the member's personal packs.
    """
    # Always fetch curated packs
    curated_result = await db.execute(
        select(StickerPack)
        .where(StickerPack.is_curated == True)  # noqa: E712
        .order_by(StickerPack.created_at.asc())
    )
    packs = list(curated_result.scalars().all())

    if include_user_packs and member_id is not None:
        # Fetch personal (user-created) packs for this member separately
        personal_result = await db.execute(
            select(StickerPack).where(
                and_(
                    StickerPack.is_curated == False,  # noqa: E712
                    StickerPack.id.in_(
                        select(Sticker.pack_id).where(Sticker.member_id == member_id)
                    ),
                )
            )
        )
        personal = list(personal_result.scalars().all())
        existing_ids = {p.id for p in packs}
        packs += [p for p in personal if p.id not in existing_ids]

    return packs


# ---------------------------------------------------------------------------
# Post to feed
# ---------------------------------------------------------------------------


async def post_to_feed(
    db: AsyncSession,
    asset_type: str,
    asset_id: UUID,
) -> StoryCreation | DrawingAsset:
    """Set posted_to_feed=True on a StoryCreation or DrawingAsset.

    Raises:
        ValidationError: asset_type is not 'stories' or 'drawings'.
        NotFoundError: Asset not found.
    """
    if asset_type == "stories":
        result = await db.execute(
            select(StoryCreation).where(StoryCreation.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise NotFoundError("StoryCreation", str(asset_id))
        asset.posted_to_feed = True
        await db.flush()
        return asset

    if asset_type == "drawings":
        result = await db.execute(
            select(DrawingAsset).where(DrawingAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise NotFoundError("DrawingAsset", str(asset_id))
        asset.posted_to_feed = True
        await db.flush()
        return asset

    raise ValidationError(
        f"Invalid asset_type '{asset_type}'. Must be 'stories' or 'drawings'."
    )


# ---------------------------------------------------------------------------
# Member creations — unified listing
# ---------------------------------------------------------------------------


async def get_member_creations(
    db: AsyncSession,
    member_id: UUID,
    asset_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict:
    """Paginated listing of a member's creative assets.

    Returns a dict with keys: art, stories, drawings (filtered by asset_type).
    """
    result: dict = {}

    if asset_type is None or asset_type == "art":
        result["art"] = await list_member_art(db, member_id, offset=offset, limit=limit)

    if asset_type is None or asset_type == "stories":
        result["stories"] = await list_member_stories(db, member_id, offset=offset, limit=limit)

    if asset_type is None or asset_type == "drawings":
        result["drawings"] = await list_member_drawings(db, member_id, offset=offset, limit=limit)

    return result
