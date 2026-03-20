"""Social risk detection models for grooming, cyberbullying, and sexting."""

import re
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

logger = structlog.get_logger()


class SocialRiskCategory(StrEnum):
    GROOMING = "grooming"
    CYBERBULLYING = "cyberbullying"
    SEXTING = "sexting"
    NONE = "none"


@dataclass
class SocialRiskResult:
    """Result of social risk classification."""

    category: SocialRiskCategory
    severity: str  # critical/high/medium/low/none
    confidence: float  # 0.0-1.0
    matched_patterns: list[str]
    risk_score: int  # 0-100
    details: dict = field(default_factory=dict)


class SocialRiskClassifier:
    """Pattern-based social risk classifier for child safety.

    Detects grooming, cyberbullying, and sexting patterns in text content.
    Each pattern has a label and weight; scores are summed per category
    and the highest-scoring category determines the result.
    """

    def __init__(self) -> None:
        self._grooming_patterns = self._build_grooming_patterns()
        self._bullying_patterns = self._build_bullying_patterns()
        self._sexting_patterns = self._build_sexting_patterns()

    def _build_grooming_patterns(self) -> list[tuple[re.Pattern, str, int]]:
        """Returns (pattern, label, weight) tuples for grooming detection."""
        return [
            (
                re.compile(
                    r"\b(you'?re?\s+(so\s+)?special|you'?re?\s+mature)\b", re.I
                ),
                "flattery",
                15,
            ),
            (
                re.compile(
                    r"\b(don'?t\s+tell\s+(anyone|your\s+(mom|dad|parents))"
                    r"|keep\s+this\s+(between\s+us|secret|private)"
                    r"|our\s+secret)\b",
                    re.I,
                ),
                "secrecy",
                25,
            ),
            (
                re.compile(
                    r"\b(i'?ll?\s+buy\s+you"
                    r"|send\s+me\s+your\s+address"
                    r"|where\s+do\s+you\s+live"
                    r"|what\s+school)\b",
                    re.I,
                ),
                "info_solicitation",
                20,
            ),
            (
                re.compile(
                    r"\b(meet\s+(me|up)\s+(alone|in\s+person|privately)"
                    r"|come\s+to\s+my)\b",
                    re.I,
                ),
                "isolation",
                30,
            ),
            (
                re.compile(
                    r"\b(you\s+can\s+trust\s+me"
                    r"|i'?m\s+your\s+(best\s+)?friend"
                    r"|no\s+one\s+understands\s+you\s+like)\b",
                    re.I,
                ),
                "trust_building",
                10,
            ),
            (
                re.compile(
                    r"\b(age\s+is\s+just\s+a\s+number"
                    r"|mature\s+for\s+your\s+age)\b",
                    re.I,
                ),
                "age_minimizing",
                30,
            ),
        ]

    def _build_bullying_patterns(self) -> list[tuple[re.Pattern, str, int]]:
        """Returns (pattern, label, weight) tuples for cyberbullying detection."""
        return [
            (
                re.compile(
                    r"\b(nobody\s+likes\s+you"
                    r"|everyone\s+hates\s+you"
                    r"|no\s+friends)\b",
                    re.I,
                ),
                "exclusion",
                20,
            ),
            (
                re.compile(r"\b(kill\s+yourself|kys|go\s+die)\b", re.I),
                "death_threat",
                40,
            ),
            (
                re.compile(
                    r"\b(i'?ll?\s+hurt\s+you"
                    r"|watch\s+your\s+back"
                    r"|you'?re?\s+dead)\b",
                    re.I,
                ),
                "threat",
                30,
            ),
            (
                re.compile(
                    r"\b(you'?re?\s+(ugly|fat|stupid|worthless|pathetic"
                    r"|a\s+loser))\b",
                    re.I,
                ),
                "derogatory",
                15,
            ),
            (
                re.compile(
                    r"\b(shut\s+up"
                    r"|no\s+one\s+asked\s+you"
                    r"|you'?re?\s+not\s+invited)\b",
                    re.I,
                ),
                "dismissal",
                10,
            ),
        ]

    def _build_sexting_patterns(self) -> list[tuple[re.Pattern, str, int]]:
        """Returns (pattern, label, weight) tuples for sexting detection."""
        return [
            (
                re.compile(
                    r"\b(send\s+(me\s+)?a?\s*(pic|photo|selfie|picture)"
                    r"|show\s+me\s+(your|ur))\b",
                    re.I,
                ),
                "image_request",
                25,
            ),
            (
                re.compile(
                    r"\b(take\s+off"
                    r"|without\s+(your|ur)\s+clothes"
                    r"|are\s+you\s+(naked|nude))\b",
                    re.I,
                ),
                "explicit_request",
                35,
            ),
            (
                re.compile(
                    r"\b(if\s+you\s+loved\s+me"
                    r"|everyone\s+does\s+it"
                    r"|it'?s\s+normal"
                    r"|don'?t\s+be\s+scared)\b",
                    re.I,
                ),
                "pressure",
                20,
            ),
            (
                re.compile(
                    r"\b(my\s+(body|privates)|your\s+(body|privates))\b",
                    re.I,
                ),
                "body_reference",
                15,
            ),
        ]

    def classify(
        self,
        text: str,
        conversation_history: list[str] | None = None,
        author_age_tier: str | None = None,
        target_age_tier: str | None = None,
    ) -> SocialRiskResult:
        """Classify text for social risks.

        Args:
            text: The message or content to classify.
            conversation_history: Previous messages for context (optional).
            author_age_tier: Age tier of the content author.
            target_age_tier: Age tier of the recipient (for DMs).

        Returns:
            SocialRiskResult with category, severity, confidence, and details.
        """
        if not text or not text.strip():
            return SocialRiskResult(
                category=SocialRiskCategory.NONE,
                severity="none",
                confidence=0.9,
                matched_patterns=[],
                risk_score=0,
            )

        full_text = text
        if conversation_history:
            full_text = " ".join(conversation_history[-5:]) + " " + text

        # Score each category
        grooming_score, grooming_matches = self._score_patterns(
            full_text, self._grooming_patterns
        )
        bullying_score, bullying_matches = self._score_patterns(
            full_text, self._bullying_patterns
        )
        sexting_score, sexting_matches = self._score_patterns(
            full_text, self._sexting_patterns
        )

        # Age tier amplification: younger targets increase risk
        if target_age_tier == "young":
            grooming_score = int(grooming_score * 1.5)
            sexting_score = int(sexting_score * 1.5)
        elif target_age_tier == "preteen":
            grooming_score = int(grooming_score * 1.2)
            sexting_score = int(sexting_score * 1.2)

        # Determine worst category
        scores = {
            SocialRiskCategory.GROOMING: (grooming_score, grooming_matches),
            SocialRiskCategory.CYBERBULLYING: (bullying_score, bullying_matches),
            SocialRiskCategory.SEXTING: (sexting_score, sexting_matches),
        }

        worst_cat = max(scores, key=lambda k: scores[k][0])
        worst_score, worst_matches = scores[worst_cat]

        if worst_score == 0:
            return SocialRiskResult(
                category=SocialRiskCategory.NONE,
                severity="none",
                confidence=0.9,
                matched_patterns=[],
                risk_score=0,
            )

        # Map score to severity
        if worst_score >= 50:
            severity = "critical"
        elif worst_score >= 30:
            severity = "high"
        elif worst_score >= 15:
            severity = "medium"
        else:
            severity = "low"

        confidence = min(0.95, worst_score / 100 + 0.3)

        logger.info(
            "social_risk_classified",
            category=worst_cat,
            severity=severity,
            risk_score=min(100, worst_score),
            matched_patterns=worst_matches,
            target_age_tier=target_age_tier,
        )

        return SocialRiskResult(
            category=worst_cat,
            severity=severity,
            confidence=confidence,
            matched_patterns=worst_matches,
            risk_score=min(100, worst_score),
            details={
                "grooming_score": grooming_score,
                "bullying_score": bullying_score,
                "sexting_score": sexting_score,
            },
        )

    def _score_patterns(
        self, text: str, patterns: list[tuple[re.Pattern, str, int]]
    ) -> tuple[int, list[str]]:
        """Score text against a list of patterns.

        Returns:
            Tuple of (total_score, matched_labels).
        """
        score = 0
        matches: list[str] = []
        for pattern, label, weight in patterns:
            if pattern.search(text):
                score += weight
                matches.append(label)
        return score, matches


# Module-level singleton
_classifier = SocialRiskClassifier()


def classify_social_risk(
    text: str,
    conversation_history: list[str] | None = None,
    author_age_tier: str | None = None,
    target_age_tier: str | None = None,
) -> SocialRiskResult:
    """Classify text for social risks using the default classifier.

    This is the public API for the social risk module.
    """
    return _classifier.classify(
        text, conversation_history, author_age_tier, target_age_tier
    )
