from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ArtifactKind = Literal["ppt", "video", "attachment"]


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
    status: str
    analysis_job_id: str
    sqs_message_id: str | None = None
    queued: bool


class SubmissionVideoAnalysisStartRequest(BaseModel):
    assignment_title: str = Field(default="Course project demo", min_length=1, max_length=255)
    required_features: list[str] = Field(default_factory=list)


class SubmissionVideoAnalysisStartResponse(BaseModel):
    submission_id: str
    video_artifact_id: str
    video_file_name: str | None
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]


class SubmissionArtifactResponse(BaseModel):
    id: str
    kind: str
    bucket: str
    object_key: str
    file_name: str | None
    content_type: str | None
    size_bytes: int | None
    status: str


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
    status: str
    error_message: str | None
    artifacts: list[SubmissionArtifactResponse]
    feedback: FeedbackReportResponse | None
    created_at: datetime
    updated_at: datetime
