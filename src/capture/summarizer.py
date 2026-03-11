"""AI conversation summarizer for parent-friendly summaries.

Uses Claude API (or configured LLM) to generate structured summaries
of children's AI conversations. Content is NOT stored — only the
processed summary output.
"""

import hashlib
import json
import os
from datetime import date as date_type, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent
from src.capture.summary_models import ConversationSummary
from src.encryption import decrypt_credential

logger = structlog.get_logger()

# Age-based detail levels
_AGE_DETAIL_LEVELS = [
    (0, 10, "full"),       # Under 10: complete summary with all quotes and context
    (11, 13, "moderate"),  # 11-13: summary + risk flags, fewer quotes
    (14, 16, "minimal"),   # 14-16: risk flags only, no quotes unless critical severity
    (17, 99, "minimal"),   # 17+: risk flags only
]


def _get_detail_level(age: int | None) -> str:
    """Determine summary detail level based on member age."""
    if age is None:
        return "full"  # Default to full if age unknown
    for min_age, max_age, level in _AGE_DETAIL_LEVELS:
        if min_age <= age <= max_age:
            return level
    return "full"


def _get_llm_config() -> tuple[str | None, str, str]:
    """Get LLM configuration from environment.

    Returns (api_key, provider, model).
    Returns (None, ..., ...) if no API key is configured.
    """
    api_key = os.environ.get("SUMMARY_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    provider = os.environ.get("SUMMARY_LLM_PROVIDER", "anthropic")
    model = os.environ.get("SUMMARY_LLM_MODEL", "claude-sonnet-4-20250514")
    return api_key, provider, model


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash for content deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_SYSTEM_PROMPT = (
    "You are a child safety analyst. Summarize this AI conversation "
    "for a parent. Focus on: topics discussed, emotional tone, any safety concerns, "
    "and notable quotes. Be factual and concise.\n\n"
    "Respond with valid JSON only, using this structure:\n"
    '{"topics": ["topic1", "topic2"], '
    '"emotional_tone": "neutral|positive|concerned|distressed", '
    '"risk_flags": ["flag1"], '
    '"key_quotes": ["quote1"], '
    '"action_needed": false, '
    '"action_reason": null, '
    '"summary_text": "Brief parent-friendly summary."}'
)


async def _call_llm(content: str, platform: str, detail_level: str) -> dict:
    """Call the LLM API to generate a structured summary.

    Returns parsed JSON dict with summary fields.
    Raises RuntimeError if the API call fails.
    """
    api_key, provider, model = _get_llm_config()
    if not api_key:
        raise RuntimeError("No LLM API key configured for summarization")

    detail_instruction = ""
    if detail_level == "moderate":
        detail_instruction = (
            "\n\nThis is for a pre-teen (11-13). Include summary and risk flags, "
            "but limit key_quotes to at most 1."
        )
    elif detail_level == "minimal":
        detail_instruction = (
            "\n\nThis is for a teenager (14+). Focus on risk flags only. "
            "Only include key_quotes if there is a critical safety concern. "
            "Keep summary_text brief (1-2 sentences max)."
        )

    user_message = (
        f"Platform: {platform}\n"
        f"---BEGIN CONVERSATION---\n{content}\n---END CONVERSATION---"
        f"{detail_instruction}"
    )

    import httpx

    if provider == "anthropic":
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": _SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["content"][0]["text"]
    else:
        raise RuntimeError(f"Unsupported LLM provider: {provider}")

    # Parse JSON response
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
        else:
            raise RuntimeError(f"Failed to parse LLM response as JSON: {text[:200]}")

    return parsed


async def summarize_conversation(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    content: str,
    platform: str,
    member_age: int | None = None,
    capture_event_id: UUID | None = None,
) -> ConversationSummary:
    """Generate parent-friendly summary using Claude API.

    Privacy: content is NOT stored in summary. Only processed output.
    Uses SUMMARY_LLM_API_KEY env var (falls back to ANTHROPIC_API_KEY).

    Returns the created ConversationSummary record.
    Raises RuntimeError if LLM API key is not configured.
    """
    api_key, provider, model = _get_llm_config()
    if not api_key:
        logger.warning(
            "summary_skipped",
            reason="no_llm_api_key",
            group_id=str(group_id),
            member_id=str(member_id),
        )
        raise RuntimeError(
            "Summarization is not available. Configure SUMMARY_LLM_API_KEY or "
            "ANTHROPIC_API_KEY to enable conversation summaries."
        )

    # Check for duplicate content
    content_hash = _compute_content_hash(content)
    existing = await db.execute(
        select(ConversationSummary).where(
            ConversationSummary.group_id == group_id,
            ConversationSummary.member_id == member_id,
            ConversationSummary.content_hash == content_hash,
        )
    )
    existing_summary = existing.scalar_one_or_none()
    if existing_summary:
        logger.info(
            "summary_dedup_hit",
            summary_id=str(existing_summary.id),
            content_hash=content_hash,
        )
        return existing_summary

    detail_level = _get_detail_level(member_age)

    # Call the LLM
    parsed = await _call_llm(content, platform, detail_level)

    # Enforce detail level constraints
    topics = parsed.get("topics", [])
    emotional_tone = parsed.get("emotional_tone", "neutral")
    risk_flags = parsed.get("risk_flags", [])
    key_quotes = parsed.get("key_quotes", [])[:3]  # max 3
    action_needed = parsed.get("action_needed", False)
    action_reason = parsed.get("action_reason")
    summary_text = parsed.get("summary_text", "")

    if detail_level == "minimal":
        # Only include quotes if action_needed (critical)
        if not action_needed:
            key_quotes = []

    if detail_level == "moderate":
        key_quotes = key_quotes[:1]

    # Validate emotional_tone
    valid_tones = {"neutral", "positive", "concerned", "distressed"}
    if emotional_tone not in valid_tones:
        emotional_tone = "neutral"

    summary = ConversationSummary(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        capture_event_id=capture_event_id,
        platform=platform,
        date=datetime.now(timezone.utc).date(),
        topics=topics,
        emotional_tone=emotional_tone,
        risk_flags=risk_flags,
        key_quotes=key_quotes,
        action_needed=action_needed,
        action_reason=action_reason[:500] if action_reason else None,
        summary_text=summary_text,
        detail_level=detail_level,
        llm_model=f"{provider}/{model}",
        content_hash=content_hash,
    )
    db.add(summary)
    await db.flush()

    logger.info(
        "summary_created",
        summary_id=str(summary.id),
        group_id=str(group_id),
        member_id=str(member_id),
        platform=platform,
        detail_level=detail_level,
        action_needed=action_needed,
    )

    return summary


async def generate_daily_summaries(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    target_date: date_type,
) -> list[ConversationSummary]:
    """Batch-summarize all enhanced captures for a member on a given date.

    Called by daily_summarization job. Looks for capture events with
    enhanced_monitoring=True and encrypted content, decrypts and summarizes each.
    """
    api_key, _, _ = _get_llm_config()
    if not api_key:
        logger.warning(
            "daily_summary_skipped",
            reason="no_llm_api_key",
            group_id=str(group_id),
            member_id=str(member_id),
        )
        return []

    # Find enhanced capture events for this member on target_date
    start_dt = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    result = await db.execute(
        select(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.member_id == member_id,
            CaptureEvent.enhanced_monitoring.is_(True),
            CaptureEvent.content_encrypted.isnot(None),
            CaptureEvent.timestamp >= start_dt,
            CaptureEvent.timestamp < end_dt,
        )
    )
    events = list(result.scalars().all())

    if not events:
        return []

    summaries = []
    for event in events:
        try:
            # Decrypt content
            content = decrypt_credential(event.content_encrypted)
            if not content:
                continue

            summary = await summarize_conversation(
                db=db,
                group_id=group_id,
                member_id=member_id,
                content=content,
                platform=event.platform,
                capture_event_id=event.id,
            )
            summaries.append(summary)
        except Exception as exc:
            logger.error(
                "daily_summary_event_error",
                event_id=str(event.id),
                error=str(exc),
            )

    logger.info(
        "daily_summaries_generated",
        group_id=str(group_id),
        member_id=str(member_id),
        date=target_date.isoformat(),
        count=len(summaries),
    )

    return summaries


async def get_member_summaries(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List summaries with pagination.

    Returns {items, total, page, page_size, total_pages}.
    """
    query = select(ConversationSummary).where(
        ConversationSummary.group_id == group_id,
        ConversationSummary.member_id == member_id,
    )

    count_query = select(func.count()).select_from(ConversationSummary).where(
        ConversationSummary.group_id == group_id,
        ConversationSummary.member_id == member_id,
    )

    if start_date:
        query = query.where(ConversationSummary.date >= start_date)
        count_query = count_query.where(ConversationSummary.date >= start_date)

    if end_date:
        query = query.where(ConversationSummary.date <= end_date)
        count_query = count_query.where(ConversationSummary.date <= end_date)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get page of results
    offset = (page - 1) * page_size
    query = query.order_by(ConversationSummary.date.desc(), ConversationSummary.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
