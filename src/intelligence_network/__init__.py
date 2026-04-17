"""Intelligence Network module — anonymized cross-customer threat signal sharing."""

from src.intelligence_network.service import (
    contribute_signal,
    fetch_signals_for_subscriber,
    submit_feedback,
    subscribe,
    unsubscribe,
)

__all__ = [
    "contribute_signal",
    "fetch_signals_for_subscriber",
    "submit_feedback",
    "subscribe",
    "unsubscribe",
]
