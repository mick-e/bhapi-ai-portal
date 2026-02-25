"""PII (Personally Identifiable Information) detection engine.

Uses 18+ regex patterns to detect PII in text content, covering:
- Email addresses
- Phone numbers (US, UK, international)
- Social Security Numbers (US)
- Credit card numbers (Visa, MasterCard, Amex)
- IBAN bank account numbers
- Passport numbers (US, UK)
- NHS numbers (UK)
- IP addresses (IPv4)
- Dates of birth / age patterns
- Physical address patterns
- Names (heuristic)
- School names
"""

import re
from dataclasses import dataclass


@dataclass
class PIIEntity:
    """A detected PII entity in text."""

    entity_type: str
    value: str
    start: int
    end: int
    confidence: float


# ---------------------------------------------------------------------------
# Pattern definitions: (name, compiled regex, confidence)
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, re.Pattern, float]] = [
    # Email address
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        0.95,
    ),
    # US phone numbers: (123) 456-7890, 123-456-7890, +1 123 456 7890
    (
        "PHONE_US",
        re.compile(r"(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b"),
        0.85,
    ),
    # UK phone numbers: +44 7xxx, 07xxx, 020 xxxx xxxx
    (
        "PHONE_UK",
        re.compile(r"(?:\+44[\s\-]?|0)(?:7\d{3}|\d{2,4})[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b"),
        0.80,
    ),
    # International phone: +XX followed by 7-15 digits
    (
        "PHONE_INTL",
        re.compile(r"\+[2-9]\d[\s\-]?\d[\s\-]?\d{4,12}\b"),
        0.70,
    ),
    # US Social Security Number: 123-45-6789
    (
        "SSN",
        re.compile(r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b"),
        0.80,
    ),
    # Credit card — Visa (4xxx xxxx xxxx xxxx)
    (
        "CREDIT_CARD_VISA",
        re.compile(r"\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        0.90,
    ),
    # Credit card — MasterCard (5[1-5]xx or 2[2-7]xx)
    (
        "CREDIT_CARD_MC",
        re.compile(r"\b(?:5[1-5]\d{2}|2[2-7]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        0.90,
    ),
    # Credit card — Amex (3[47]xx xxxxxx xxxxx)
    (
        "CREDIT_CARD_AMEX",
        re.compile(r"\b3[47]\d{2}[\s\-]?\d{6}[\s\-]?\d{5}\b"),
        0.90,
    ),
    # IBAN (2-letter country code + 2 check digits + up to 30 alphanumeric)
    (
        "IBAN",
        re.compile(r"\b[A-Z]{2}\d{2}[\s]?[A-Z0-9]{4}[\s]?(?:[A-Z0-9]{4}[\s]?){1,7}[A-Z0-9]{1,4}\b"),
        0.85,
    ),
    # US passport number (9 digits)
    (
        "PASSPORT_US",
        re.compile(r"\b[A-Z]?\d{8,9}\b"),
        0.40,  # Low confidence — many false positives, raised by context
    ),
    # UK passport number (9 digits)
    (
        "PASSPORT_UK",
        re.compile(r"\b\d{9}\b"),
        0.30,  # Very low standalone — needs context boost
    ),
    # NHS number (UK): 3-digit groups separated by spaces: 123 456 7890
    (
        "NHS_NUMBER",
        re.compile(r"\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b"),
        0.70,
    ),
    # IPv4 address
    (
        "IP_ADDRESS",
        re.compile(r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
        0.85,
    ),
    # Date of birth patterns: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, "born on", "DOB"
    (
        "DATE_OF_BIRTH",
        re.compile(
            r"(?:(?:born\s+(?:on\s+)?|DOB[:\s]+|date\s+of\s+birth[:\s]+)"
            r"[\d]{1,2}[/\-\.][\d]{1,2}[/\-\.][\d]{2,4})"
            r"|(?:\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b)",
            re.IGNORECASE,
        ),
        0.75,
    ),
    # Age patterns: "I am 12 years old", "age: 14", "12 year old"
    (
        "AGE",
        re.compile(
            r"(?:i\s+am\s+|i'm\s+|age[:\s]+|aged?\s+)(\d{1,2})(?:\s+years?\s+old)?|"
            r"\b(\d{1,2})\s+(?:year|yr)s?\s+old\b",
            re.IGNORECASE,
        ),
        0.80,
    ),
    # Physical address: number + street name + (St|Ave|Rd|Dr|Blvd|Lane|Way|Ct|Pl)
    (
        "ADDRESS",
        re.compile(
            r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Lane|Ln|Way|Court|Ct|Place|Pl)\b",
            re.IGNORECASE,
        ),
        0.75,
    ),
    # Full name heuristic: "My name is Firstname Lastname"
    (
        "PERSON_NAME",
        re.compile(
            r"(?:(?:my\s+name\s+is|i'm|i\s+am|called)\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            re.IGNORECASE,
        ),
        0.70,
    ),
    # School name heuristic: "I go to / attend / study at X School/Academy/College"
    (
        "SCHOOL_NAME",
        re.compile(
            r"(?:(?:go\s+to|attend|study\s+at|enrolled?\s+(?:at|in))\s+)"
            r"([A-Z][A-Za-z\s]+?(?:School|Academy|College|High|Primary|Secondary|Grammar|Prep))",
            re.IGNORECASE,
        ),
        0.75,
    ),
]


def detect(text: str) -> list[PIIEntity]:
    """Detect all PII entities in the given text.

    Returns a list of PIIEntity objects sorted by position (start offset).
    Overlapping matches are de-duplicated by keeping the higher-confidence match.
    """
    if not text or not text.strip():
        return []

    entities: list[PIIEntity] = []

    for entity_type, pattern, base_confidence in _PII_PATTERNS:
        for match in pattern.finditer(text):
            # Use the first capturing group if one exists, otherwise the full match
            if match.lastindex:
                value = match.group(1)
                start = match.start(1)
                end = match.end(1)
            else:
                value = match.group(0)
                start = match.start()
                end = match.end()

            # Context boost: if the surrounding text contains related keywords,
            # increase confidence for lower-confidence patterns
            confidence = _apply_context_boost(text, start, end, entity_type, base_confidence)

            entities.append(
                PIIEntity(
                    entity_type=entity_type,
                    value=value,
                    start=start,
                    end=end,
                    confidence=confidence,
                )
            )

    # Sort by position, then de-duplicate overlaps
    entities.sort(key=lambda e: (e.start, -e.confidence))
    return _deduplicate_overlaps(entities)


def mask(text: str, replacement_template: str = "<{entity_type}>") -> str:
    """Replace all detected PII in *text* with masked tokens.

    By default each PII span is replaced with ``<ENTITY_TYPE>``, e.g.
    ``<EMAIL>``, ``<PHONE_US>``.  The *replacement_template* may contain
    ``{entity_type}`` which will be formatted per entity.

    Returns the masked text.
    """
    entities = detect(text)
    if not entities:
        return text

    # Process from end to start so that offsets remain valid
    result = list(text)
    for entity in sorted(entities, key=lambda e: e.start, reverse=True):
        replacement = replacement_template.format(entity_type=entity.entity_type)
        result[entity.start : entity.end] = list(replacement)

    return "".join(result)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CONTEXT_KEYWORDS: dict[str, list[str]] = {
    "PASSPORT_US": ["passport", "travel document", "passport number"],
    "PASSPORT_UK": ["passport", "travel document", "passport number", "HMPO"],
    "NHS_NUMBER": ["nhs", "national health", "health service", "nhs number"],
    "SSN": ["social security", "ssn", "social sec"],
    "DATE_OF_BIRTH": ["birthday", "born", "dob", "date of birth"],
}


def _apply_context_boost(
    text: str,
    start: int,
    end: int,
    entity_type: str,
    base_confidence: float,
) -> float:
    """Boost confidence if surrounding context mentions entity-related keywords."""
    keywords = _CONTEXT_KEYWORDS.get(entity_type)
    if not keywords:
        return base_confidence

    # Look at a window of 100 chars before and after the match
    window_start = max(0, start - 100)
    window_end = min(len(text), end + 100)
    window = text[window_start:window_end].lower()

    for keyword in keywords:
        if keyword in window:
            return min(base_confidence + 0.25, 1.0)

    return base_confidence


def _deduplicate_overlaps(entities: list[PIIEntity]) -> list[PIIEntity]:
    """Remove overlapping entities, keeping the higher-confidence one."""
    if not entities:
        return entities

    result: list[PIIEntity] = []
    for entity in entities:
        # Check if this entity overlaps with the last accepted entity
        if result and entity.start < result[-1].end:
            # Keep the one with higher confidence
            if entity.confidence > result[-1].confidence:
                result[-1] = entity
        else:
            result.append(entity)

    return result
