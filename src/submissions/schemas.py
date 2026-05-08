from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ArtifactKind = Literal["repo", "ppt", "video", "live_audio", "attachment"]
RunStatus = Literal["submitted", "queued", "running", "completed", "failed"]
ArtifactStatus = Literal["submitted", "processing", "completed", "failed"]
AnalysisJobType = Literal[
    "submission_analysis",
    "git_analysis",
    "ppt_analysis",
    "video_analysis",
    "final_grading_analysis",
]


class RubricCriterionInput(BaseModel):
    category: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1)
    max_score: float = Field(gt=0)


class ArtifactInput(BaseModel):
    kind: ArtifactKind
    object_key: str = Field(min_length=1)
    file_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    kind: ArtifactKind = "attachment"
    submission_id: str | None = None


class PresignedUploadResponse(BaseModel):
    upload_url: str
    method: Literal["PUT"]
    bucket: str
    object_key: str
    headers: dict[str, str]
    expires_in: int


class SubmissionCreateRequest(BaseModel):
    event_id: str | None = None
    team_name: str = Field(min_length=1, max_length=255)
    repo_url: str | None = None
    branch: str | None = None
    assignment_id: str | None = None
    submitter_email: str | None = None
    rubric_criteria: list[RubricCriterionInput] = Field(default_factory=list)
    artifacts: list[ArtifactInput] = Field(default_factory=list)


class SubmissionResponse(BaseModel):
    id: str
    status: RunStatus
    queued: bool


class SubmissionArtifactAnalysisStartResponse(BaseModel):
    submission_id: str
    job_id: str
    job_type: AnalysisJobType
    status: RunStatus
    queued: bool
    sqs_message_id: str | None = None
    run_id: str | None = None


class SubmissionArtifactResponse(BaseModel):
    id: str
    kind: ArtifactKind
    bucket: str
    object_key: str
    file_name: str | None
    content_type: str | None
    size_bytes: int | None
    status: ArtifactStatus


class FeedbackScoreResponse(BaseModel):
    category: str
    score: float
    max_score: float | None
    comment: str | None


class FeedbackReportResponse(BaseModel):
    summary: str | None
    raw_result: dict[str, Any] | None
    scores: list[FeedbackScoreResponse]


class SubmissionDetailResponse(BaseModel):
    id: str
    event_id: str | None
    team_name: str
    repo_url: str | None
    branch: str | None
    status: RunStatus
    error_message: str | None
    artifacts: list[SubmissionArtifactResponse]
    feedback: FeedbackReportResponse | None
    created_at: datetime
    updated_at: datetime
