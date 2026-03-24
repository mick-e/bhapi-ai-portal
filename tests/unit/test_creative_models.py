"""Unit tests for creative module models and schemas."""

import uuid

import pytest
from pydantic import ValidationError

from src.creative.models import (
    ArtGeneration,
    DrawingAsset,
    Sticker,
    StickerPack,
    StoryCreation,
    StoryTemplate,
)
from src.creative.schemas import (
    ArtGenerationCreate,
    DrawingAssetCreate,
    StickerCreate,
    StickerPackCreate,
    StoryCreationCreate,
    StoryTemplateCreate,
)
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_member(session):
    """Create a group + member and return (group_id, member_id)."""
    from src.groups.models import GroupMember

    group, owner_id = await make_test_group(session)
    member = GroupMember(
        group_id=group.id,
        user_id=owner_id,
        role="parent",
        display_name="Test Parent",
    )
    session.add(member)
    await session.flush()
    return group.id, member.id


# ---------------------------------------------------------------------------
# ArtGeneration model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_art_generation_create(test_session):
    """ArtGeneration can be created with valid data."""
    group_id, member_id = await _make_member(test_session)
    art = ArtGeneration(
        member_id=member_id,
        group_id=group_id,
        prompt="A purple dragon flying over a rainbow",
        sanitized_prompt="A purple dragon flying over a rainbow",
    )
    test_session.add(art)
    await test_session.flush()

    result = await test_session.get(ArtGeneration, art.id)
    assert result is not None
    assert result.prompt == "A purple dragon flying over a rainbow"
    assert result.model == "dalle3"
    assert result.cost == 0.0
    assert result.moderation_status == "pending"
    assert result.image_url is None


@pytest.mark.asyncio
async def test_art_generation_defaults(test_session):
    """ArtGeneration default values are applied correctly."""
    group_id, member_id = await _make_member(test_session)
    art = ArtGeneration(
        member_id=member_id,
        group_id=group_id,
        prompt="Test prompt",
        sanitized_prompt="Test prompt",
    )
    test_session.add(art)
    await test_session.flush()

    assert art.moderation_status == "pending"
    assert art.model == "dalle3"
    assert art.cost == 0.0
    assert art.image_url is None


@pytest.mark.asyncio
async def test_art_generation_with_image_url(test_session):
    """ArtGeneration stores image_url when provided."""
    group_id, member_id = await _make_member(test_session)
    art = ArtGeneration(
        member_id=member_id,
        group_id=group_id,
        prompt="A sunny meadow",
        sanitized_prompt="A sunny meadow",
        image_url="https://example.com/images/art123.png",
        cost=0.02,
        moderation_status="approved",
    )
    test_session.add(art)
    await test_session.flush()

    result = await test_session.get(ArtGeneration, art.id)
    assert result.image_url == "https://example.com/images/art123.png"
    assert result.cost == 0.02
    assert result.moderation_status == "approved"


# ---------------------------------------------------------------------------
# StoryTemplate model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_story_template_create(test_session):
    """StoryTemplate can be created with all required fields."""
    template = StoryTemplate(
        title="The Lost Dragon",
        theme="adventure",
        content_template="Once upon a time, {{hero}} discovered a {{object}}...",
        min_age_tier="young",
        template_type="fill_in_blank",
    )
    test_session.add(template)
    await test_session.flush()

    result = await test_session.get(StoryTemplate, template.id)
    assert result is not None
    assert result.title == "The Lost Dragon"
    assert result.theme == "adventure"
    assert result.min_age_tier == "young"
    assert result.template_type == "fill_in_blank"


# ---------------------------------------------------------------------------
# StoryCreation model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_story_creation_create(test_session):
    """StoryCreation can be created without a template."""
    _, member_id = await _make_member(test_session)
    story = StoryCreation(
        member_id=member_id,
        template_id=None,
        content="My adventure began on a rainy Tuesday...",
    )
    test_session.add(story)
    await test_session.flush()

    result = await test_session.get(StoryCreation, story.id)
    assert result is not None
    assert result.content == "My adventure began on a rainy Tuesday..."
    assert result.moderation_status == "pending"
    assert result.posted_to_feed is False
    assert result.template_id is None


@pytest.mark.asyncio
async def test_story_creation_with_template(test_session):
    """StoryCreation correctly references an existing template."""
    _, member_id = await _make_member(test_session)
    template = StoryTemplate(
        title="Friendship Forever",
        theme="friendship",
        content_template="{{name}} and {{friend}} decided to...",
        min_age_tier="preteen",
        template_type="fill_in_blank",
    )
    test_session.add(template)
    await test_session.flush()

    story = StoryCreation(
        member_id=member_id,
        template_id=template.id,
        content="Alice and Bob decided to build a treehouse.",
    )
    test_session.add(story)
    await test_session.flush()

    result = await test_session.get(StoryCreation, story.id)
    assert result.template_id == template.id


# ---------------------------------------------------------------------------
# StickerPack + Sticker model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sticker_pack_create(test_session):
    """StickerPack can be created with correct defaults."""
    pack = StickerPack(
        name="Summer Fun",
        category="seasonal",
    )
    test_session.add(pack)
    await test_session.flush()

    result = await test_session.get(StickerPack, pack.id)
    assert result is not None
    assert result.name == "Summer Fun"
    assert result.category == "seasonal"
    assert result.is_curated is False


@pytest.mark.asyncio
async def test_sticker_pack_curated(test_session):
    """StickerPack can be marked as curated."""
    pack = StickerPack(
        name="Bhapi Branded",
        category="branded",
        is_curated=True,
    )
    test_session.add(pack)
    await test_session.flush()

    result = await test_session.get(StickerPack, pack.id)
    assert result.is_curated is True


@pytest.mark.asyncio
async def test_sticker_create_curated(test_session):
    """Sticker can be created with null member_id for curated content."""
    pack = StickerPack(name="Edu Pack", category="educational", is_curated=True)
    test_session.add(pack)
    await test_session.flush()

    sticker = Sticker(
        pack_id=pack.id,
        member_id=None,
        image_url="https://example.com/stickers/star.png",
    )
    test_session.add(sticker)
    await test_session.flush()

    result = await test_session.get(Sticker, sticker.id)
    assert result is not None
    assert result.member_id is None
    assert result.moderation_status == "pending"
    assert result.image_url == "https://example.com/stickers/star.png"


@pytest.mark.asyncio
async def test_sticker_create_user_generated(test_session):
    """Sticker can be created with member_id for user-generated content."""
    _, member_id = await _make_member(test_session)
    pack = StickerPack(name="My Creations", category="user_created")
    test_session.add(pack)
    await test_session.flush()

    sticker = Sticker(
        pack_id=pack.id,
        member_id=member_id,
        image_url="https://example.com/stickers/custom.png",
    )
    test_session.add(sticker)
    await test_session.flush()

    result = await test_session.get(Sticker, sticker.id)
    assert result.member_id == member_id


# ---------------------------------------------------------------------------
# DrawingAsset model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drawing_asset_create(test_session):
    """DrawingAsset can be created with valid data."""
    group_id, member_id = await _make_member(test_session)
    drawing = DrawingAsset(
        member_id=member_id,
        group_id=group_id,
        image_url="https://example.com/drawings/abc123.png",
    )
    test_session.add(drawing)
    await test_session.flush()

    result = await test_session.get(DrawingAsset, drawing.id)
    assert result is not None
    assert result.image_url == "https://example.com/drawings/abc123.png"
    assert result.moderation_status == "pending"
    assert result.posted_to_feed is False


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


def test_art_generation_schema_prompt_too_long():
    """ArtGenerationCreate rejects prompts exceeding 500 chars."""
    with pytest.raises(ValidationError):
        ArtGenerationCreate(prompt="x" * 501)


def test_art_generation_schema_valid_prompt():
    """ArtGenerationCreate accepts a valid prompt."""
    schema = ArtGenerationCreate(prompt="A sunny day at the beach")
    assert schema.prompt == "A sunny day at the beach"
    assert schema.model == "dalle3"


def test_story_template_schema_invalid_theme():
    """StoryTemplateCreate rejects unknown theme values."""
    with pytest.raises(ValidationError):
        StoryTemplateCreate(
            title="Test",
            theme="invalid_theme",
            content_template="...",
            min_age_tier="young",
            template_type="fill_in_blank",
        )


def test_story_template_schema_invalid_template_type():
    """StoryTemplateCreate rejects unknown template_type values."""
    with pytest.raises(ValidationError):
        StoryTemplateCreate(
            title="Test",
            theme="adventure",
            content_template="...",
            min_age_tier="young",
            template_type="bad_type",
        )


def test_story_template_schema_valid():
    """StoryTemplateCreate accepts all valid field combinations."""
    schema = StoryTemplateCreate(
        title="Mystery at Midnight",
        theme="mystery",
        content_template="The clue was hidden in {{place}}...",
        min_age_tier="teen",
        template_type="free_write",
    )
    assert schema.theme == "mystery"
    assert schema.template_type == "free_write"
    assert schema.min_age_tier == "teen"


def test_sticker_pack_schema_invalid_category():
    """StickerPackCreate rejects unknown category values."""
    with pytest.raises(ValidationError):
        StickerPackCreate(name="Bad Pack", category="illegal_category")


def test_sticker_pack_schema_valid():
    """StickerPackCreate accepts all valid categories."""
    for cat in ("branded", "seasonal", "educational", "user_created"):
        schema = StickerPackCreate(name="Test Pack", category=cat)
        assert schema.category == cat


def test_story_creation_schema_valid():
    """StoryCreationCreate accepts None template_id."""
    schema = StoryCreationCreate(template_id=None, content="My story begins here.")
    assert schema.template_id is None
    assert schema.content == "My story begins here."


def test_story_creation_schema_with_template_id():
    """StoryCreationCreate accepts a UUID template_id."""
    tid = uuid.uuid4()
    schema = StoryCreationCreate(template_id=tid, content="Continuing the adventure...")
    assert schema.template_id == tid


def test_drawing_asset_schema_valid():
    """DrawingAssetCreate accepts a valid image_url."""
    schema = DrawingAssetCreate(image_url="https://example.com/draw.png")
    assert schema.image_url == "https://example.com/draw.png"
