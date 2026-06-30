from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ai_sdr.config import REPORTS_DIR, SETTINGS

EVENTS_PATH = REPORTS_DIR / "observability" / "events.jsonl"
TRACES_PATH = REPORTS_DIR / "observability" / "traces.jsonl"


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


def trace_span(
    name: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a local trace span shaped for future Langfuse/Phoenix adapters."""
    TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)
    span = {
        "timestamp": datetime.now(UTC).isoformat(),
        "name": name,
        "sink": SETTINGS.observability_sink,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "metadata": {
            "langfuse_host": SETTINGS.langfuse_host,
            "phoenix_endpoint": SETTINGS.phoenix_endpoint,
            **(metadata or {}),
        },
    }
    with TRACES_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(span, default=str) + "\n")


def read_recent_traces(limit: int = 20) -> list[dict[str, Any]]:
    """Read the most recent local trace spans."""
    if not TRACES_PATH.exists():
        return []
    lines = TRACES_PATH.read_text(encoding="utf-8").splitlines()
    traces: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            traces.append(parsed)
    return traces
