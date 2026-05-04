from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from src.video_agent.models.schemas import DemoVideoJobRecord


class DemoVideoJobStore:
    """Thread-safe in-memory store for background video analysis jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, DemoVideoJobRecord] = {}

    def create_job(self, *, video_path: str | None = None) -> DemoVideoJobRecord:
        job_id = str(uuid.uuid4())
        record = DemoVideoJobRecord(job_id=job_id, status="pending", video_path=video_path)
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> DemoVideoJobRecord | None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return None
            return rec.model_copy()

    def update(
        self,
        job_id: str,
        *,
        status: Literal["pending", "running", "completed", "failed"] | None = None,
        video_path: str | None = None,
        raw_output: str | None = None,
        parsed: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            data = rec.model_dump()
            if status is not None:
                data["status"] = status
            if video_path is not None:
                data["video_path"] = video_path
            if raw_output is not None:
                data["raw_output"] = raw_output
            if parsed is not None:
                data["parsed"] = parsed
            if error is not None:
                data["error"] = error
            data["updated_at"] = datetime.now(timezone.utc)
            self._jobs[job_id] = DemoVideoJobRecord.model_validate(data)


JOB_STORE = DemoVideoJobStore()
