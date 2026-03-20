"""Content moderation pipeline module.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.moderation.service import submit_for_moderation, takedown_content

__all__ = ["submit_for_moderation", "takedown_content"]
