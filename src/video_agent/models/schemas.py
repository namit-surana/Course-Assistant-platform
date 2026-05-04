from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class DemoVideoJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]


class DemoVideoJobRecord(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    video_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_output: str | None = None
    parsed: dict[str, Any] | None = None
    error: str | None = None
