"""Extract short/medium/long-term ratings from the Portfolio Manager's decision.

The PM now produces three separate ratings (see
:func:`tradingagents.agents.schemas.render_pm_decision`) and stores them
directly in the graph state.  For backwards compatibility with callers
that only have the rendered markdown text, the module also supports
re-parsing via :func:`tradingagents.agents.utils.rating.parse_ratings`.
"""

from __future__ import annotations

from typing import Any

from tradingagents.agents.utils.rating import parse_rating, parse_ratings


def extract_signal_from_state(state: dict) -> dict[str, str]:
    """Return ``{"short": ..., "medium": ..., "long": ...}`` from graph state.

    Prefers the dedicated state fields; falls back to parsing ``final_trade_decision`` text.
    """
    text = state.get("final_trade_decision", "")
    ratings = {}
    for key in ("short", "medium", "long"):
        field = f"{key}_term_rating"
        val = state.get(field, "")
        if val:
            ratings[key] = val
        elif text:
            ratings_dict = parse_ratings(text)
            ratings[key] = ratings_dict.get(key, parse_rating(text))
        else:
            ratings[key] = "Hold"
    return ratings


class SignalProcessor:
    """Read the three time-horizon ratings from a Portfolio Manager decision."""

    def __init__(self, quick_thinking_llm: Any = None):
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, state_or_text: dict | str) -> dict[str, str] | str:
        """Return a dict of three ratings or a single rating for backwards compat.

        When passed a dict (graph state), returns ``{"short": ..., "medium": ..., "long": ...}``.
        When passed a string, returns a single ``parse_rating`` result (legacy path).
        """
        if isinstance(state_or_text, dict):
            return extract_signal_from_state(state_or_text)
        return parse_rating(state_or_text)
