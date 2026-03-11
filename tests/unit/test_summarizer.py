"""Unit tests for the conversation summarizer module.

Tests mock LLM responses, age-based detail level selection,
and content deduplication by content_hash.
"""

import hashlib
import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_test_group


# ─── Age-based detail level ──────────────────────────────────────────────────

def test_get_detail_level_under_10():
    from src.capture.summarizer import _get_detail_level
    assert _get_detail_level(5) == "full"
    assert _get_detail_level(9) == "full"
    assert _get_detail_level(10) == "full"


def test_get_detail_level_11_to_13():
    from src.capture.summarizer import _get_detail_level
    assert _get_detail_level(11) == "moderate"
    assert _get_detail_level(12) == "moderate"
    assert _get_detail_level(13) == "moderate"


def test_get_detail_level_14_to_16():
    from src.capture.summarizer import _get_detail_level
    assert _get_detail_level(14) == "minimal"
    assert _get_detail_level(15) == "minimal"
    assert _get_detail_level(16) == "minimal"


def test_get_detail_level_17_plus():
    from src.capture.summarizer import _get_detail_level
    assert _get_detail_level(17) == "minimal"
    assert _get_detail_level(18) == "minimal"


def test_get_detail_level_none_defaults_to_full():
    from src.capture.summarizer import _get_detail_level
    assert _get_detail_level(None) == "full"


# ─── Content hash ────────────────────────────────────────────────────────────

def test_compute_content_hash():
    from src.capture.summarizer import _compute_content_hash
    content = "Hello, how are you?"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert _compute_content_hash(content) == expected


def test_compute_content_hash_different_content():
    from src.capture.summarizer import _compute_content_hash
    hash1 = _compute_content_hash("Hello")
    hash2 = _compute_content_hash("World")
    assert hash1 != hash2


# ─── LLM config ──────────────────────────────────────────────────────────────

def test_get_llm_config_defaults():
    """When no env vars set, api_key is None."""
    with patch.dict("os.environ", {}, clear=True):
        from src.capture.summarizer import _get_llm_config
        api_key, provider, model = _get_llm_config()
        assert api_key is None
        assert provider == "anthropic"


def test_get_llm_config_with_summary_key():
    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test-123"}):
        from src.capture.summarizer import _get_llm_config
        api_key, _, _ = _get_llm_config()
        assert api_key == "sk-test-123"


def test_get_llm_config_falls_back_to_anthropic_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-456"}, clear=True):
        from src.capture.summarizer import _get_llm_config
        api_key, _, _ = _get_llm_config()
        assert api_key == "sk-ant-456"


# ─── Summarize conversation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summarize_no_api_key(test_session: AsyncSession):
    """Summarization raises RuntimeError when no API key is set."""
    from src.capture.summarizer import summarize_conversation

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="not available"):
            await summarize_conversation(
                db=test_session,
                group_id=uuid4(),
                member_id=uuid4(),
                content="Hello AI",
                platform="chatgpt",
            )


@pytest.mark.asyncio
async def test_summarize_creates_summary(test_session: AsyncSession):
    """Summarization creates a ConversationSummary record."""
    from src.capture.summarizer import summarize_conversation

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Child",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    mock_response = {
        "topics": ["homework", "math"],
        "emotional_tone": "positive",
        "risk_flags": [],
        "key_quotes": ["I need help with algebra"],
        "action_needed": False,
        "action_reason": None,
        "summary_text": "Child discussed math homework assistance.",
    }

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock, return_value=mock_response):
            summary = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content="Help me with my algebra homework",
                platform="chatgpt",
                member_age=9,
            )

    assert summary.id is not None
    assert summary.group_id == group.id
    assert summary.member_id == member.id
    assert summary.platform == "chatgpt"
    assert summary.topics == ["homework", "math"]
    assert summary.emotional_tone == "positive"
    assert summary.detail_level == "full"
    assert summary.action_needed is False
    assert summary.summary_text == "Child discussed math homework assistance."


@pytest.mark.asyncio
async def test_summarize_dedup_by_content_hash(test_session: AsyncSession):
    """Duplicate content returns existing summary instead of creating new one."""
    from src.capture.summarizer import summarize_conversation, _compute_content_hash
    from src.capture.summary_models import ConversationSummary

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Child",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    content = "Help me with my algebra homework"
    content_hash = _compute_content_hash(content)

    # Pre-create a summary with the same hash
    existing = ConversationSummary(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        date=date.today(),
        topics=["math"],
        emotional_tone="neutral",
        risk_flags=[],
        key_quotes=[],
        action_needed=False,
        summary_text="Existing summary",
        detail_level="full",
        llm_model="anthropic/claude-sonnet-4-20250514",
        content_hash=content_hash,
    )
    test_session.add(existing)
    await test_session.flush()

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        # _call_llm should NOT be called (dedup hit)
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock) as mock_llm:
            result = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content=content,
                platform="chatgpt",
            )

    assert result.id == existing.id
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_moderate_detail_limits_quotes(test_session: AsyncSession):
    """Moderate detail level (age 11-13) limits key_quotes to 1."""
    from src.capture.summarizer import summarize_conversation

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Preteen",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    mock_response = {
        "topics": ["social media"],
        "emotional_tone": "neutral",
        "risk_flags": [],
        "key_quotes": ["quote 1", "quote 2", "quote 3"],
        "action_needed": False,
        "action_reason": None,
        "summary_text": "Discussion about social media.",
    }

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock, return_value=mock_response):
            summary = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content="Tell me about Instagram",
                platform="gemini",
                member_age=12,
            )

    assert summary.detail_level == "moderate"
    assert len(summary.key_quotes) <= 1


@pytest.mark.asyncio
async def test_summarize_minimal_detail_strips_quotes(test_session: AsyncSession):
    """Minimal detail level (age 14+) strips quotes unless action_needed."""
    from src.capture.summarizer import summarize_conversation

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Teen",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    mock_response = {
        "topics": ["coding"],
        "emotional_tone": "positive",
        "risk_flags": [],
        "key_quotes": ["I want to learn Python"],
        "action_needed": False,
        "action_reason": None,
        "summary_text": "Discussing coding.",
    }

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock, return_value=mock_response):
            summary = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content="Teach me Python",
                platform="copilot",
                member_age=15,
            )

    assert summary.detail_level == "minimal"
    assert summary.key_quotes == []  # Stripped because no action needed


@pytest.mark.asyncio
async def test_summarize_minimal_keeps_quotes_when_action_needed(test_session: AsyncSession):
    """Minimal detail keeps quotes when action_needed is True."""
    from src.capture.summarizer import summarize_conversation

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Teen",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    mock_response = {
        "topics": ["personal info"],
        "emotional_tone": "concerned",
        "risk_flags": ["pii_shared"],
        "key_quotes": ["Here is my address"],
        "action_needed": True,
        "action_reason": "Child shared personal address with AI",
        "summary_text": "Child shared personal info.",
    }

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock, return_value=mock_response):
            summary = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content="My address is 123 Main St",
                platform="claude",
                member_age=16,
            )

    assert summary.detail_level == "minimal"
    assert summary.action_needed is True
    assert len(summary.key_quotes) == 1  # Kept because critical


@pytest.mark.asyncio
async def test_summarize_invalid_tone_defaults_neutral(test_session: AsyncSession):
    """Invalid emotional_tone from LLM defaults to neutral."""
    from src.capture.summarizer import summarize_conversation

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Child",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    mock_response = {
        "topics": [],
        "emotional_tone": "INVALID_TONE",
        "risk_flags": [],
        "key_quotes": [],
        "action_needed": False,
        "action_reason": None,
        "summary_text": "Normal chat.",
    }

    with patch.dict("os.environ", {"SUMMARY_LLM_API_KEY": "sk-test"}):
        with patch("src.capture.summarizer._call_llm", new_callable=AsyncMock, return_value=mock_response):
            summary = await summarize_conversation(
                db=test_session,
                group_id=group.id,
                member_id=member.id,
                content="Hi there",
                platform="grok",
            )

    assert summary.emotional_tone == "neutral"


# ─── get_member_summaries ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_member_summaries_pagination(test_session: AsyncSession):
    """get_member_summaries returns paginated results."""
    from src.capture.summarizer import get_member_summaries, _compute_content_hash
    from src.capture.summary_models import ConversationSummary

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Child",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    # Create 5 summaries
    for i in range(5):
        s = ConversationSummary(
            id=uuid4(),
            group_id=group.id,
            member_id=member.id,
            platform="chatgpt",
            date=date.today(),
            topics=[f"topic-{i}"],
            emotional_tone="neutral",
            risk_flags=[],
            key_quotes=[],
            action_needed=False,
            summary_text=f"Summary {i}",
            detail_level="full",
            llm_model="test",
            content_hash=_compute_content_hash(f"content-{i}"),
        )
        test_session.add(s)
    await test_session.flush()

    result = await get_member_summaries(
        db=test_session,
        group_id=group.id,
        member_id=member.id,
        page=1,
        page_size=2,
    )

    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert result["total_pages"] == 3


@pytest.mark.asyncio
async def test_get_member_summaries_date_filter(test_session: AsyncSession):
    """get_member_summaries filters by date range."""
    from datetime import timedelta
    from src.capture.summarizer import get_member_summaries, _compute_content_hash
    from src.capture.summary_models import ConversationSummary

    group, owner_id = await make_test_group(test_session)
    from src.groups.models import GroupMember
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        display_name="Child",
        role="member",
    )
    test_session.add(member)
    await test_session.flush()

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Today's summary
    s1 = ConversationSummary(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        date=today,
        topics=[],
        emotional_tone="neutral",
        risk_flags=[],
        key_quotes=[],
        action_needed=False,
        summary_text="Today",
        detail_level="full",
        llm_model="test",
        content_hash=_compute_content_hash("today"),
    )
    # Yesterday's summary
    s2 = ConversationSummary(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        date=yesterday,
        topics=[],
        emotional_tone="neutral",
        risk_flags=[],
        key_quotes=[],
        action_needed=False,
        summary_text="Yesterday",
        detail_level="full",
        llm_model="test",
        content_hash=_compute_content_hash("yesterday"),
    )
    test_session.add_all([s1, s2])
    await test_session.flush()

    # Filter for today only
    result = await get_member_summaries(
        db=test_session,
        group_id=group.id,
        member_id=member.id,
        start_date=today,
        end_date=today,
    )

    assert result["total"] == 1
    assert result["items"][0].summary_text == "Today"


# ─── generate_daily_summaries ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_daily_summaries_skips_without_key(test_session: AsyncSession):
    """generate_daily_summaries returns empty list when no API key."""
    from src.capture.summarizer import generate_daily_summaries

    with patch.dict("os.environ", {}, clear=True):
        result = await generate_daily_summaries(
            db=test_session,
            group_id=uuid4(),
            member_id=uuid4(),
            target_date=date.today(),
        )

    assert result == []
