from __future__ import annotations

import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any


def log_event(level: str, event: str, **fields: Any) -> None:
    """Emit one machine-readable event per line for local and CI logs."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "level": level.upper(),
        "event": event,
        **fields,
    }
    stream = sys.stderr if level.upper() in {"ERROR", "CRITICAL"} else sys.stdout
    print(json.dumps(payload, sort_keys=True, default=str), file=stream, flush=True)


@dataclass
class CollectionMetrics:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    finished_at: str | None = None
    duration_ms: int = 0
    status: str = "running"
    brands_processed: int = 0
    queries_attempted: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_requests: int = 0
    api_errors: int = 0
    raw_results: int = 0
    items_published: int = 0
    validation_errors: int = 0
    error: str | None = None
    _started_monotonic: float = field(default_factory=monotonic, repr=False)

    def finish(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.error = error
        self.finished_at = datetime.now(UTC).isoformat(timespec="seconds")
        self.duration_ms = round((monotonic() - self._started_monotonic) * 1000)

    def snapshot(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("_started_monotonic", None)
        return payload


def save_run_metrics(path: Path, metrics: CollectionMetrics, history_limit: int = 30) -> None:
    history: list[dict[str, Any]] = []
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(current, dict) and isinstance(current.get("history"), list):
                history = current["history"]
        except (json.JSONDecodeError, OSError):
            history = []

    snapshot = metrics.snapshot()
    history.append(snapshot)
    payload = {"latest": snapshot, "history": history[-history_limit:]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
