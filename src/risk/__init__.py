"""Risk & safety engine module.

Public interface for cross-module communication.
Other modules should import only from this file, never from internal submodules.
"""

from src.risk.engine import process_event
from src.risk.schemas import RiskClassification
from src.risk.taxonomy import ALL_CATEGORIES, ALL_SEVERITIES, RISK_CATEGORIES

# Public interface for cross-module access
from .models import ContentExcerpt, RiskConfig, RiskEvent

__all__ = [
    "process_event",
    "RiskClassification",
    "ALL_CATEGORIES",
    "ALL_SEVERITIES",
    "RISK_CATEGORIES",
    "ContentExcerpt",
    "RiskConfig",
    "RiskEvent",
]
