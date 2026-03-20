"""Fast-path keyword classifier for content moderation.

Provides <100ms text classification using keyword matching.
Results: BLOCK (auto-reject), ALLOW (auto-approve for pre-pub), UNCERTAIN (send to AI).
"""

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

logger = structlog.get_logger()


class FilterAction(StrEnum):
    BLOCK = "block"  # Auto-reject, critical/high severity match
    ALLOW = "allow"  # No concerning keywords found
    UNCERTAIN = "uncertain"  # Needs AI review


@dataclass
class FilterResult:
    """Result of keyword classification."""

    action: FilterAction
    matched_keywords: list[str] = field(default_factory=list)
    severity: str | None = None  # critical/high/medium/None
    confidence: float = 0.0  # 0.0-1.0


class KeywordFilter:
    """Fast keyword-based text classifier.

    Uses set-based lookup for O(1) single-word matching and substring
    scanning for multi-word phrases. Maintains separate keyword lists
    by severity level.
    """

    def __init__(self) -> None:
        # Per-severity keyword sets (normalized lowercase)
        self._critical_words: set[str] = set()
        self._high_words: set[str] = set()
        self._medium_words: set[str] = set()
        # Multi-word phrases stored separately for substring matching
        self._critical_phrases: set[str] = set()
        self._high_phrases: set[str] = set()
        self._medium_phrases: set[str] = set()
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default keyword lists."""
        # Critical: immediate danger keywords — child safety focus
        critical_all = {
            "suicide",
            "kill myself",
            "self-harm",
            "self harm",
            "end my life",
            "child porn",
            "csam",
            "nude children",
            "want to die",
            "hurt myself",
        }
        # High: serious concern
        high_all = {
            "drugs",
            "weapon",
            "gun",
            "knife attack",
            "porn",
            "xxx",
            "naked",
            "sexting",
            "bully",
            "threat",
            "kill you",
            "cocaine",
            "heroin",
            "meth",
        }
        # Medium: warrants review
        medium_all = {
            "hate",
            "stupid",
            "ugly",
            "loser",
            "dumb",
            "cheat",
            "homework answers",
            "test answers",
            "idiot",
            "shut up",
        }

        # Split into single-word and multi-word sets
        for kw in critical_all:
            if " " in kw:
                self._critical_phrases.add(kw)
            else:
                self._critical_words.add(kw)

        for kw in high_all:
            if " " in kw:
                self._high_phrases.add(kw)
            else:
                self._high_words.add(kw)

        for kw in medium_all:
            if " " in kw:
                self._medium_phrases.add(kw)
            else:
                self._medium_words.add(kw)

    def _normalize(self, text: str) -> str:
        """Normalize text: lowercase, strip accents, collapse whitespace."""
        text = text.lower()
        # Strip accents (e.g., e-acute -> e)
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _find_matches(
        self,
        words: set[str],
        normalized: str,
        word_set: set[str],
        phrase_set: set[str],
    ) -> set[str]:
        """Find keyword matches from both single words and phrases."""
        matches = words & word_set
        for phrase in phrase_set:
            if phrase in normalized:
                matches.add(phrase)
        return matches

    def classify_text(
        self, text: str, age_tier: str | None = None
    ) -> FilterResult:
        """Classify text content.

        Args:
            text: The text to classify.
            age_tier: Optional age tier (young/preteen/teen) for
                      tier-specific sensitivity.

        Returns:
            FilterResult with action, matched keywords, severity, confidence.
        """
        if not text or not text.strip():
            return FilterResult(
                action=FilterAction.ALLOW,
                matched_keywords=[],
                severity=None,
                confidence=0.9,
            )

        normalized = self._normalize(text)
        words = set(normalized.split())

        # Check critical first (highest severity)
        critical_matches = self._find_matches(
            words, normalized, self._critical_words, self._critical_phrases
        )
        if critical_matches:
            return FilterResult(
                action=FilterAction.BLOCK,
                matched_keywords=sorted(critical_matches),
                severity="critical",
                confidence=0.95,
            )

        # Check high severity
        high_matches = self._find_matches(
            words, normalized, self._high_words, self._high_phrases
        )
        if high_matches:
            # Young tier: block on high severity too
            if age_tier == "young":
                return FilterResult(
                    action=FilterAction.BLOCK,
                    matched_keywords=sorted(high_matches),
                    severity="high",
                    confidence=0.85,
                )
            return FilterResult(
                action=FilterAction.UNCERTAIN,
                matched_keywords=sorted(high_matches),
                severity="high",
                confidence=0.7,
            )

        # Check medium severity
        medium_matches = self._find_matches(
            words, normalized, self._medium_words, self._medium_phrases
        )
        if medium_matches:
            # Young/preteen: uncertain for medium (needs AI review)
            if age_tier in ("young", "preteen"):
                return FilterResult(
                    action=FilterAction.UNCERTAIN,
                    matched_keywords=sorted(medium_matches),
                    severity="medium",
                    confidence=0.5,
                )
            # Teen: allow (medium severity is informational for teens)
            return FilterResult(
                action=FilterAction.ALLOW,
                matched_keywords=sorted(medium_matches),
                severity="medium",
                confidence=0.6,
            )

        # No matches
        return FilterResult(
            action=FilterAction.ALLOW,
            matched_keywords=[],
            severity=None,
            confidence=0.9,
        )

    def add_keywords(
        self, severity: str, keywords: set[str]
    ) -> None:
        """Add custom keywords to a severity level.

        Args:
            severity: One of 'critical', 'high', 'medium'.
            keywords: Set of keywords to add.
        """
        word_sets = {
            "critical": (self._critical_words, self._critical_phrases),
            "high": (self._high_words, self._high_phrases),
            "medium": (self._medium_words, self._medium_phrases),
        }
        if severity not in word_sets:
            raise ValueError(
                f"Invalid severity '{severity}'. Must be: critical, high, medium"
            )

        word_set, phrase_set = word_sets[severity]
        for kw in keywords:
            normalized = kw.lower().strip()
            if " " in normalized:
                phrase_set.add(normalized)
            else:
                word_set.add(normalized)

    def remove_keywords(
        self, severity: str, keywords: set[str]
    ) -> None:
        """Remove keywords from a severity level."""
        word_sets = {
            "critical": (self._critical_words, self._critical_phrases),
            "high": (self._high_words, self._high_phrases),
            "medium": (self._medium_words, self._medium_phrases),
        }
        if severity not in word_sets:
            raise ValueError(
                f"Invalid severity '{severity}'. Must be: critical, high, medium"
            )

        word_set, phrase_set = word_sets[severity]
        for kw in keywords:
            normalized = kw.lower().strip()
            word_set.discard(normalized)
            phrase_set.discard(normalized)


# Module-level singleton
_filter = KeywordFilter()


def classify_text(text: str, age_tier: str | None = None) -> FilterResult:
    """Classify text using the default keyword filter."""
    return _filter.classify_text(text, age_tier)


def get_filter() -> KeywordFilter:
    """Get the module-level singleton filter instance."""
    return _filter
