"""Intelligence module — social graph analysis, abuse signals, behavioral baselines.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.intelligence.service import (
    create_abuse_signal,
    create_baseline,
    create_graph_edge,
    get_abuse_signals,
    get_baseline,
    get_member_edges,
    resolve_abuse_signal,
    run_age_pattern_check,
    run_graph_analysis,
    run_influence_mapping,
    run_isolation_check,
)

__all__ = [
    "create_abuse_signal",
    "create_baseline",
    "create_graph_edge",
    "get_abuse_signals",
    "get_baseline",
    "get_member_edges",
    "resolve_abuse_signal",
    "run_age_pattern_check",
    "run_graph_analysis",
    "run_influence_mapping",
    "run_isolation_check",
]
