"""Manage analysis history by scanning existing log files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _results_dir() -> Path:
    return Path.home() / ".tradingagents" / "logs"


def get_history() -> list[dict[str, str]]:
    """Scan saved analysis logs and return a sorted list (newest first).

    Each entry: {"ticker": "300750", "date": "2026-05-12", "path": "/abs/path/...json"}
    """
    root = _results_dir()
    if not root.exists():
        return []

    entries: list[dict[str, str]] = []
    for log_file in root.rglob("full_states_log_*.json"):
        match = re.search(r"full_states_log_(\d{4}-\d{2}-\d{2})\.json$", log_file.name)
        if not match:
            continue
        date = match.group(1)
        ticker = log_file.parent.parent.name
        mtime = log_file.stat().st_mtime
        entries.append({"ticker": ticker, "date": date, "path": str(log_file), "mtime": mtime})

    entries.sort(key=lambda e: e["mtime"], reverse=True)
    return entries


def delete_analysis(path: str) -> None:
    """Delete an analysis log file and clean up empty parent directories."""
    p = Path(path)
    if p.exists():
        p.unlink()
    for parent in [p.parent, p.parent.parent]:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


def load_analysis(path: str) -> dict[str, Any]:
    """Load a saved analysis JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_signal(state: dict[str, Any]) -> dict[str, str]:
    """Extract short/medium/long term signals from a final state dict.

    Returns ``{"short": "Sell", "medium": "Hold", "long": "Buy"}``.
    Prefers dedicated state fields; falls back to parsing ``final_trade_decision`` text.
    """
    from tradingagents.graph.signal_processing import extract_signal_from_state

    return extract_signal_from_state(state)


def extract_signal_legacy(state: dict[str, Any]) -> str:
    """Legacy single-signal extraction for backward compat (e.g. history listing)."""
    signals = extract_signal(state)
    return signals.get("short", "Hold")
