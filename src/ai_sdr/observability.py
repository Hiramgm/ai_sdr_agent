from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib import error, request

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


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with request.urlopen(req, timeout=5):
        return


def _forward_to_langfuse(span: dict[str, Any]) -> None:
    if not SETTINGS.langfuse_public_key or not SETTINGS.langfuse_secret_key:
        return
    host = (SETTINGS.langfuse_host or "https://cloud.langfuse.com").rstrip("/")
    trace_id = str(uuid.uuid4())
    batch = [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": span["timestamp"],
            "body": {
                "id": trace_id,
                "name": span["name"],
                "input": span["inputs"],
                "output": span["outputs"],
                "metadata": span["metadata"],
            },
        }
    ]
    credentials = base64.b64encode(
        f"{SETTINGS.langfuse_public_key}:{SETTINGS.langfuse_secret_key}".encode()
    ).decode()
    _post_json(
        f"{host}/api/public/ingestion",
        {"batch": batch},
        {"Authorization": f"Basic {credentials}"},
    )


def _forward_to_phoenix(span: dict[str, Any]) -> None:
    if not SETTINGS.phoenix_endpoint:
        return
    endpoint = SETTINGS.phoenix_endpoint.rstrip("/")
    _post_json(endpoint, span, {})


def _forward_trace(span: dict[str, Any]) -> None:
    sink = SETTINGS.observability_sink.lower()
    if sink in {"langfuse", "hosted"}:
        try:
            _forward_to_langfuse(span)
        except (error.URLError, error.HTTPError, TimeoutError, OSError):
            pass
    if sink in {"phoenix", "hosted"}:
        try:
            _forward_to_phoenix(span)
        except (error.URLError, error.HTTPError, TimeoutError, OSError):
            pass


def trace_span(
    name: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a local trace span and optionally forward to hosted sinks."""
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
    _forward_trace(span)


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
