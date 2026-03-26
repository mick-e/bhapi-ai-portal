"""Unit tests for the creative service — art, stories, stickers, drawings."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.creative.models import (
    ArtGeneration,
    StickerPack,
    StoryTemplate,
)
from src.creative.service import (
    _sanitize_prompt,
    create_custom_sticker,
    create_story,
    generate_art,
    get_member_creations,
    get_sticker_packs,
    get_story_templates,
    list_member_art,
    list_member_drawings,
    list_member_stories,
    post_to_feed,
    save_drawing,
)
from src.exceptions import NotFoundError, RateLimitError, ValidationError
from src.groups.models import Group, GroupMember

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession, **kwargs) -> User:
    uid = kwargs.pop("id", None) or uuid.uuid4()
    user = User(
        id=uid,
        email=kwargs.pop("email", f"test-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.pop("display_name", "Test User"),
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_group(session: AsyncSession, owner_id: uuid.UUID) -> Group:
    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=owner_id,
        settings={},
    )
    session.add(group)
    await session.flush()
    return group


async def _make_member(
    session: AsyncSession,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    date_of_birth=None,
) -> GroupMember:
    today = datetime.now(timezone.utc).date()
    if date_of_birth is None:
        # Default: 7 years old (young tier)
        dob = today.replace(year=today.year - 7)
        date_of_birth = datetime(dob.year, dob.month, dob.day)

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        user_id=user_id,
        role="member",
        display_name="Child Member",
        date_of_birth=date_of_birth,
    )
    session.add(member)
    await session.flush()
    return member


def _dob_for_age(age: int) -> datetime:
    today = datetime.now(timezone.utc).date()
    dob = today.replace(year=today.year - age)
    return datetime(dob.year, dob.month, dob.day)


# ---------------------------------------------------------------------------
# _sanitize_prompt
# ---------------------------------------------------------------------------


class TestSanitizePrompt:
    def test_clean_prompt_passes(self):
        result = _sanitize_prompt("a beautiful sunset over mountains")
        assert result == "a beautiful sunset over mountains"

    def test_blocked_word_nude_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("a nude figure standing")

    def test_blocked_word_violence_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("extreme violence scene")

    def test_blocked_word_drugs_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("cartoon about drugs")

    def test_blocked_word_weapons_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("a collection of weapons")

    def test_blocked_word_gun_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("a person holding a gun")

    def test_blocked_word_case_insensitive(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("NUDE beach scene")

    def test_blocked_word_kill_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("how to kill time")

    def test_blocked_word_sex_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("sex education poster")

    def test_blocked_word_porn_raises(self):
        with pytest.raises(ValidationError):
            _sanitize_prompt("this is porn")

    def test_prompt_stripped(self):
        result = _sanitize_prompt("  happy cat  ")
        assert result == "happy cat"


# ---------------------------------------------------------------------------
# generate_art
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_art_clean_prompt(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id, _dob_for_age(7))

    art = await generate_art(
        test_session, member_id=member.id, group_id=group.id, prompt="a happy dragon"
    )
    await test_session.flush()

    assert art.id is not None
    assert art.prompt == "a happy dragon"
    assert art.sanitized_prompt == "a happy dragon"
    assert art.moderation_status == "pending"
    assert art.group_id == group.id
    assert art.member_id == member.id


@pytest.mark.asyncio
async def test_generate_art_blocked_prompt_raises(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id, _dob_for_age(7))

    with pytest.raises(ValidationError):
        await generate_art(
            test_session, member_id=member.id, group_id=group.id, prompt="nude portrait"
        )


@pytest.mark.asyncio
async def test_generate_art_rate_limit_young_child(test_session: AsyncSession):
    """11th art request for a young child should raise RateLimitError."""
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id, _dob_for_age(7))

    # Insert 10 art records today
    now = datetime.now(timezone.utc)
    for i in range(10):
        art = ArtGeneration(
            member_id=member.id,
            group_id=group.id,
            prompt=f"prompt {i}",
            sanitized_prompt=f"prompt {i}",
            model="dalle3",
            moderation_status="pending",
        )
        # Override created_at to be today
        art.created_at = now - timedelta(minutes=i)
        test_session.add(art)
    await test_session.flush()

    with pytest.raises(RateLimitError):
        await generate_art(
            test_session,
            member_id=member.id,
            group_id=group.id,
            prompt="another cat",
        )


@pytest.mark.asyncio
async def test_generate_art_rate_limit_preteen(test_session: AsyncSession):
    """Preteen (age 11) has a limit of 25/day."""
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id, _dob_for_age(11))

    now = datetime.now(timezone.utc)
    for i in range(25):
        art = ArtGeneration(
            member_id=member.id,
            group_id=group.id,
            prompt=f"prompt {i}",
            sanitized_prompt=f"prompt {i}",
            model="dalle3",
            moderation_status="pending",
        )
        art.created_at = now - timedelta(minutes=i)
        test_session.add(art)
    await test_session.flush()

    with pytest.raises(RateLimitError):
        await generate_art(
            test_session,
            member_id=member.id,
            group_id=group.id,
            prompt="flowers",
        )


@pytest.mark.asyncio
async def test_generate_art_rate_limit_not_exceeded(test_session: AsyncSession):
    """9 art requests for young child should still allow a 10th."""
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id, _dob_for_age(7))

    now = datetime.now(timezone.utc)
    for i in range(9):
        art = ArtGeneration(
            member_id=member.id,
            group_id=group.id,
            prompt=f"prompt {i}",
            sanitized_prompt=f"prompt {i}",
            model="dalle3",
            moderation_status="pending",
        )
        art.created_at = now - timedelta(minutes=i)
        test_session.add(art)
    await test_session.flush()

    # Should succeed (10th request within limit)
    art = await generate_art(
        test_session,
        member_id=member.id,
        group_id=group.id,
        prompt="a rainbow",
    )
    assert art is not None


# ---------------------------------------------------------------------------
# Story templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_story_templates_returns_all(test_session: AsyncSession):
    tmpl1 = StoryTemplate(
        title="Adventure Template",
        theme="adventure",
        content_template="Once upon a time {hero} went to {place}...",
        min_age_tier="young",
        template_type="fill_in_blank",
    )
    tmpl2 = StoryTemplate(
        title="Mystery Template",
        theme="mystery",
        content_template="The mystery began when {event} happened.",
        min_age_tier="preteen",
        template_type="free_write",
    )
    test_session.add_all([tmpl1, tmpl2])
    await test_session.flush()

    templates = await get_story_templates(test_session)
    assert len(templates) >= 2


@pytest.mark.asyncio
async def test_get_story_templates_filtered_by_age_tier(test_session: AsyncSession):
    tmpl = StoryTemplate(
        title="Teen Story",
        theme="fantasy",
        content_template="In a world where {magic} exists...",
        min_age_tier="teen",
        template_type="free_write",
    )
    test_session.add(tmpl)
    await test_session.flush()

    teen_templates = await get_story_templates(test_session, age_tier="teen")
    assert all(t.min_age_tier == "teen" for t in teen_templates)

    young_templates = await get_story_templates(test_session, age_tier="young")
    assert all(t.min_age_tier == "young" for t in young_templates)


# ---------------------------------------------------------------------------
# Story creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_story_without_template(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    story = await create_story(
        test_session,
        member_id=member.id,
        content="My story about a dragon",
    )
    assert story.id is not None
    assert story.content == "My story about a dragon"
    assert story.template_id is None
    assert story.moderation_status == "pending"
    assert story.posted_to_feed is False


@pytest.mark.asyncio
async def test_create_story_with_valid_template(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    tmpl = StoryTemplate(
        title="Adventure Template",
        theme="adventure",
        content_template="Once upon a time...",
        min_age_tier="young",
        template_type="fill_in_blank",
    )
    test_session.add(tmpl)
    await test_session.flush()

    story = await create_story(
        test_session,
        member_id=member.id,
        content="My adventure story",
        template_id=tmpl.id,
    )
    assert story.template_id == tmpl.id


@pytest.mark.asyncio
async def test_create_story_with_invalid_template_raises(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    with pytest.raises(NotFoundError):
        await create_story(
            test_session,
            member_id=member.id,
            content="Story content",
            template_id=uuid.uuid4(),  # non-existent
        )


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_drawing_creates_drawing_asset(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    drawing = await save_drawing(
        test_session,
        member_id=member.id,
        group_id=group.id,
        image_url="https://cdn.example.com/drawing.png",
    )
    assert drawing.id is not None
    assert drawing.image_url == "https://cdn.example.com/drawing.png"
    assert drawing.moderation_status == "pending"
    assert drawing.posted_to_feed is False


# ---------------------------------------------------------------------------
# Stickers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_custom_sticker_creates_personal_pack(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    sticker = await create_custom_sticker(
        test_session,
        member_id=member.id,
        image_url="https://cdn.example.com/sticker.png",
    )
    assert sticker.id is not None
    assert sticker.member_id == member.id
    assert sticker.moderation_status == "pending"


@pytest.mark.asyncio
async def test_create_custom_sticker_reuses_personal_pack(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    sticker1 = await create_custom_sticker(
        test_session,
        member_id=member.id,
        image_url="https://cdn.example.com/s1.png",
    )
    sticker2 = await create_custom_sticker(
        test_session,
        member_id=member.id,
        image_url="https://cdn.example.com/s2.png",
    )
    # Both stickers should be in the same pack
    assert sticker1.pack_id == sticker2.pack_id


@pytest.mark.asyncio
async def test_get_sticker_packs_returns_curated(test_session: AsyncSession):
    pack = StickerPack(
        name="Emoji Fun",
        category="branded",
        is_curated=True,
    )
    test_session.add(pack)
    await test_session.flush()

    packs = await get_sticker_packs(test_session)
    pack_ids = {p.id for p in packs}
    assert pack.id in pack_ids


@pytest.mark.asyncio
async def test_get_sticker_packs_excludes_user_packs_by_default(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    await create_custom_sticker(
        test_session,
        member_id=member.id,
        image_url="https://cdn.example.com/s.png",
    )

    packs = await get_sticker_packs(test_session, include_user_packs=False)
    assert all(p.is_curated for p in packs)


# ---------------------------------------------------------------------------
# Post to feed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_to_feed_updates_story(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    story = await create_story(test_session, member_id=member.id, content="Test story")
    assert story.posted_to_feed is False

    updated = await post_to_feed(test_session, asset_type="stories", asset_id=story.id)
    assert updated.posted_to_feed is True


@pytest.mark.asyncio
async def test_post_to_feed_updates_drawing(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    drawing = await save_drawing(
        test_session,
        member_id=member.id,
        group_id=group.id,
        image_url="https://cdn.example.com/d.png",
    )
    updated = await post_to_feed(test_session, asset_type="drawings", asset_id=drawing.id)
    assert updated.posted_to_feed is True


@pytest.mark.asyncio
async def test_post_to_feed_invalid_type_raises(test_session: AsyncSession):
    with pytest.raises(ValidationError):
        await post_to_feed(test_session, asset_type="invalid", asset_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_post_to_feed_not_found_raises(test_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await post_to_feed(test_session, asset_type="stories", asset_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# get_member_creations — pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_member_creations_returns_all_types(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    await generate_art(
        test_session, member_id=member.id, group_id=group.id, prompt="colorful bird"
    )
    await create_story(test_session, member_id=member.id, content="A tale")
    await save_drawing(
        test_session, member_id=member.id, group_id=group.id,
        image_url="https://cdn.example.com/d.png",
    )

    result = await get_member_creations(test_session, member_id=member.id)
    assert len(result["art"]) >= 1
    assert len(result["stories"]) >= 1
    assert len(result["drawings"]) >= 1


@pytest.mark.asyncio
async def test_get_member_creations_filtered_by_type(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    await generate_art(
        test_session, member_id=member.id, group_id=group.id, prompt="sunshine"
    )
    await create_story(test_session, member_id=member.id, content="Story text")

    result = await get_member_creations(test_session, member_id=member.id, asset_type="art")
    assert "art" in result
    assert "stories" not in result
    assert "drawings" not in result


@pytest.mark.asyncio
async def test_get_member_creations_pagination(test_session: AsyncSession):
    user = await _make_user(test_session)
    group = await _make_group(test_session, user.id)
    member = await _make_member(test_session, group.id, user.id)

    for i in range(5):
        await create_story(
            test_session, member_id=member.id, content=f"Story number {i}"
        )

    result_page1 = await get_member_creations(
        test_session, member_id=member.id, asset_type="stories", offset=0, limit=3
    )
    result_page2 = await get_member_creations(
        test_session, member_id=member.id, asset_type="stories", offset=3, limit=3
    )
    assert len(result_page1["stories"]) == 3
    assert len(result_page2["stories"]) == 2


@pytest.mark.asyncio
async def test_list_member_art_empty(test_session: AsyncSession):
    """list_member_art returns empty list for member with no art."""
    art = await list_member_art(test_session, member_id=uuid.uuid4())
    assert art == []


@pytest.mark.asyncio
async def test_list_member_stories_empty(test_session: AsyncSession):
    stories = await list_member_stories(test_session, member_id=uuid.uuid4())
    assert stories == []


@pytest.mark.asyncio
async def test_list_member_drawings_empty(test_session: AsyncSession):
    drawings = await list_member_drawings(test_session, member_id=uuid.uuid4())
    assert drawings == []
