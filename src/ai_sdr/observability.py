from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ai_sdr.config import REPORTS_DIR

EVENTS_PATH = REPORTS_DIR / "observability" / "events.jsonl"


def log_event(event_type: str, payload: dict[str, Any]) -> None:
    """Append a local structured event for demo-friendly observability."""
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }
    with EVENTS_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, default=str) + "\n")


def read_recent_events(limit: int = 20) -> list[dict[str, Any]]:
    """Read the most recent local observability events."""
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events
