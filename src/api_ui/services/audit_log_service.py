from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class AuditLogService:
    """Append-only JSONL audit logger for analysis runs."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self._lock = Lock()

    def log(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "run_id": run_id,
            **payload,
        }
        with self._lock:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"{run_id}.jsonl"
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
