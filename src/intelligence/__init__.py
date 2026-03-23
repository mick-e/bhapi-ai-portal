"""Intelligence module — social graph analysis, abuse signals, behavioral baselines.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.intelligence.correlation import (
    create_enriched_alert,
    create_rule,
    evaluate_event,
    get_enriched_alert,
    get_rules,
    update_rule,
)
from src.intelligence.event_bus import (
    ALL_CHANNELS,
    EVENT_AI_SESSION,
    EVENT_DEVICE,
    EVENT_LOCATION,
    EVENT_SOCIAL_ACTIVITY,
    publish_event,
    subscribe,
)
from src.intelligence.scoring import (
    compute_unified_score,
    get_score_breakdown,
    get_score_history,
    get_score_trend,
)
from src.intelligence.service import (
    compute_member_baseline,
    create_abuse_signal,
    create_baseline,
    create_graph_edge,
    detect_member_deviation,
    get_abuse_signals,
    get_baseline,
    get_member_baseline_summary,
    get_member_edges,
    resolve_abuse_signal,
    run_age_pattern_check,
    run_baseline_batch,
    run_graph_analysis,
    run_influence_mapping,
    run_isolation_check,
)

__all__ = [
    # Correlation
    "create_enriched_alert",
    "create_rule",
    "evaluate_event",
    "get_enriched_alert",
    "get_rules",
    "update_rule",
    # Event bus
    "ALL_CHANNELS",
    "EVENT_AI_SESSION",
    "EVENT_DEVICE",
    "EVENT_LOCATION",
    "EVENT_SOCIAL_ACTIVITY",
    "publish_event",
    "subscribe",
    # Scoring
    "compute_unified_score",
    "get_score_breakdown",
    "get_score_history",
    "get_score_trend",
    # Service
    "compute_member_baseline",
    "create_abuse_signal",
    "create_baseline",
    "create_graph_edge",
    "detect_member_deviation",
    "get_abuse_signals",
    "get_baseline",
    "get_member_baseline_summary",
    "get_member_edges",
    "resolve_abuse_signal",
    "run_age_pattern_check",
    "run_baseline_batch",
    "run_graph_analysis",
    "run_influence_mapping",
    "run_isolation_check",
]
