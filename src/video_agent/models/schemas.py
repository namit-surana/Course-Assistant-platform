from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class DemoVideoRubricRow(BaseModel):
    id: str
    score: float = Field(ge=0, le=5)
    evidence: str
    timestamps: str


class DemoVideoFeatureCoverageRow(BaseModel):
    feature: str
    status: Literal["shown", "partial", "not_shown", "not_applicable"]
    evidence: str


class DemoVideoAnalysisOutput(BaseModel):
    summary: str
    rubric: list[DemoVideoRubricRow]
    feature_coverage: list[DemoVideoFeatureCoverageRow]
    gaps_and_risks: list[str] = Field(default_factory=list)
    limitations: str = ""


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
