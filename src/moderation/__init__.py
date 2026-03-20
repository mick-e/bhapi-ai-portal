"""Content moderation pipeline module.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.moderation.keyword_filter import FilterAction, FilterResult, classify_text
from src.moderation.service import submit_for_moderation, takedown_content

__all__ = [
    "FilterAction",
    "FilterResult",
    "classify_text",
    "submit_for_moderation",
    "takedown_content",
]
