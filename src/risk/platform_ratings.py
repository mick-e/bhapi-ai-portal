"""AI platform safety ratings for public consumption.

Provides baseline safety ratings for each monitored AI platform,
combining static assessments with aggregate data from the DB when available.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

# The 10 AI platforms monitored by Bhapi
PLATFORM_RATINGS: list[dict] = [
    {
        "platform": "ChatGPT",
        "safety_score": 72,
        "risk_level": "medium",
        "categories_of_concern": [
            "age-inappropriate content generation",
            "homework plagiarism",
            "PII disclosure in prompts",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Gemini",
        "safety_score": 70,
        "risk_level": "medium",
        "categories_of_concern": [
            "integrated with personal Google data",
            "age-inappropriate content generation",
            "limited parental controls",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Copilot",
        "safety_score": 74,
        "risk_level": "medium",
        "categories_of_concern": [
            "code generation without understanding",
            "academic integrity risks",
            "limited content filtering for minors",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Claude",
        "safety_score": 85,
        "risk_level": "low",
        "categories_of_concern": [
            "homework assistance misuse",
            "extended conversational engagement",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Grok",
        "safety_score": 45,
        "risk_level": "high",
        "categories_of_concern": [
            "minimal content safety filters",
            "explicit content generation",
            "political bias and misinformation",
            "no parental controls",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Character.AI",
        "safety_score": 38,
        "risk_level": "high",
        "categories_of_concern": [
            "emotional dependency and parasocial relationships",
            "companion chatbot addiction",
            "age-inappropriate roleplay",
            "self-harm ideation in conversations",
            "insufficient age verification",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Replika",
        "safety_score": 40,
        "risk_level": "high",
        "categories_of_concern": [
            "romantic and emotional dependency",
            "companion chatbot addiction",
            "inappropriate content with minors",
            "mental health manipulation",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Pi",
        "safety_score": 68,
        "risk_level": "medium",
        "categories_of_concern": [
            "emotional engagement by design",
            "limited parental visibility",
            "data privacy concerns",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Perplexity",
        "safety_score": 75,
        "risk_level": "medium",
        "categories_of_concern": [
            "unfiltered web search results",
            "misinformation propagation",
            "limited content safety for minors",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
    {
        "platform": "Poe",
        "safety_score": 55,
        "risk_level": "medium",
        "categories_of_concern": [
            "access to unfiltered third-party bots",
            "inconsistent safety across models",
            "limited content moderation",
            "user-created bots with no safety review",
        ],
        "last_updated": "2026-03-13T00:00:00Z",
    },
]


def _score_to_risk_level(score: float) -> str:
    """Convert a numeric safety score to a risk level label."""
    if score >= 70:
        return "low"
    if score >= 50:
        return "medium"
    return "high"


async def get_platform_ratings(
    db: AsyncSession | None = None,
) -> list[dict]:
    """Return platform safety ratings, optionally enriched with DB aggregate data.

    If a database session is provided, the function will attempt to blend
    static baselines with aggregate risk event counts from the DB.  If the
    DB query fails or no session is given, static baselines are returned
    unchanged.
    """
    ratings = [r.copy() for r in PLATFORM_RATINGS]

    if db is not None:
        try:
            from src.capture.models import CaptureEvent
            from src.risk.models import RiskEvent

            # Count risk events per platform from real data
            stmt = (
                select(
                    CaptureEvent.platform,
                    func.count(RiskEvent.id).label("risk_count"),
                )
                .join(CaptureEvent, RiskEvent.capture_event_id == CaptureEvent.id)
                .group_by(CaptureEvent.platform)
            )
            result = await db.execute(stmt)
            platform_risk_counts: dict[str, int] = {}
            for row in result.all():
                if row[0]:
                    platform_risk_counts[row[0].lower()] = row[1]

            if platform_risk_counts:
                log.info(
                    "platform_ratings_enriched",
                    platform_count=len(platform_risk_counts),
                )
                # Adjust scores slightly based on real incident volume
                # (simple blending — DB data nudges static baselines)
                max_count = max(platform_risk_counts.values()) or 1
                for rating in ratings:
                    key = rating["platform"].lower().replace(".", "").replace(" ", "")
                    count = platform_risk_counts.get(key, 0)
                    if count > 0:
                        # Penalty proportional to incident share (max -10 pts)
                        penalty = int((count / max_count) * 10)
                        adjusted = max(0, rating["safety_score"] - penalty)
                        rating["safety_score"] = adjusted
                        rating["risk_level"] = _score_to_risk_level(adjusted)
                        rating["last_updated"] = (
                            datetime.now(timezone.utc).isoformat()
                        )
        except Exception:
            log.warning("platform_ratings_db_enrichment_failed", exc_info=True)

    return ratings
