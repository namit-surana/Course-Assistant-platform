from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


RunStatus = Literal["queued", "running", "completed", "failed"]


class JobStatusResponse(BaseModel):
    job_id: str
    submission_id: str
    job_type: Literal[
        "submission_analysis",
        "git_analysis",
        "ppt_analysis",
        "video_analysis",
        "final_grading_analysis",
    ]
    status: RunStatus
    attempts: int
    error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
