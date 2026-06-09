"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (Buy, Overweight, Hold, Underweight, Sell) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision)
- The signal processor (rating extracted for downstream consumers)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.
"""

from __future__ import annotations

import re
from typing import Tuple


# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: Tuple[str, ...] = (
    "Buy", "Overweight", "Hold", "Underweight", "Sell",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Chinese A-stock equivalents for each rating tier
_CN_TO_EN: dict[str, str] = {
    "买入": "Buy",
    "增持": "Overweight",
    "持有": "Hold",
    "减持": "Underweight",
    "卖出": "Sell",
}
_CN_SET = set(_CN_TO_EN.keys())

# Matches "Rating: X" / "rating - X" / "Rating: **X**" — tolerates markdown
# bold wrappers and either a colon or hyphen separator.
_RATING_LABEL_RE = re.compile(r"rating.*?[:\-][\s*]*(\w+)", re.IGNORECASE)


_HORIZON_LABELS: dict[str, str] = {
    "短线": "short",
    "中线": "medium",
    "长线": "long",
}

# Matches "**短线评级**: Sell" / "**中线评级**:Hold" / "**长线评级**: <Buy>"
_HORIZON_RE = re.compile(
    r"\*\*(?P<label>" + "|".join(_HORIZON_LABELS) + r")评级[\s*]*:[\s*]*[<]?(?P<rating>\w+)",
)


def _to_en(word: str) -> str | None:
    """Convert a Chinese or English rating word to canonical English form."""
    w = word.strip("*:.,<> ")
    if not w:
        return None
    low = w.lower()
    if low in _RATING_SET:
        return low.capitalize()
    if w in _CN_TO_EN:
        return _CN_TO_EN[w]
    return None


def parse_ratings(text: str) -> dict[str, str]:
    """Extract short/medium/long term ratings from rendered PM decision.

    Returns a dict like ``{"short": "Sell", "medium": "Hold", "long": "Buy"}``.
    Only labels found in the text are included; callers should fall back to
    ``parse_rating`` for any missing horizon.
    """
    ratings: dict[str, str] = {}
    for m in _HORIZON_RE.finditer(text):
        label = m.group("label")
        rating = m.group("rating")
        en = _to_en(rating)
        if en:
            ratings[_HORIZON_LABELS[label]] = en
    return ratings


def parse_rating(text: str, default: str = "Hold") -> str:
    """Heuristically extract a 5-tier rating from prose text.

    Three-pass strategy:
    1. Look for an explicit "Rating: X" label (tolerant of markdown bold).
    2. Scan for known rating words (English or Chinese) in the text.
    3. Return the **last** rating word found.

    Returns a Title-cased rating string, or ``default`` if no rating word appears.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m and m.group(1).lower() in _RATING_SET:
            return m.group(1).capitalize()

    last: str | None = None
    for line in text.splitlines():
        for word in line.split():
            en = _to_en(word)
            if en:
                last = en
    if last:
        return last

    return default
