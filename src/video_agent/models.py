from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VideoAnalysisMode(str, Enum):
    FULL_VIDEO = "full_video"
    TRANSCRIPTION_ONLY = "transcription_only"


class LargeVideoDecision(str, Enum):
    REQUIRE_CONFIRMATION = "require_confirmation"
    PROCEED_FULL_VIDEO = "proceed_full_video"
    PROCEED_TRANSCRIPTION_ONLY = "proceed_transcription_only"


class RubricCriterion(BaseModel):
    category: str = Field(..., min_length=1)
    max_score: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)


class CriterionScore(BaseModel):
    category: str
    score: float
    max_score: float
    comment: str
    evidence: str = ""

    @field_validator("score")
    @classmethod
    def score_must_be_non_negative(cls, value: float) -> float:
        return max(0.0, float(value))


class VideoAnalysisResult(BaseModel):
    criteria_scores: list[CriterionScore]
    video_summary: str
    analysis_mode: VideoAnalysisMode
    total_score: float = 0.0
    max_total_score: float = 0.0
    warnings: list[str] = []
    metadata: dict[str, Any] = {}


class LargeVideoPrompt(BaseModel):
    requires_confirmation: bool = True
    file_size_bytes: int
    file_size_mb: float
    threshold_mb: float
    message: str
    options: list[dict[str, str]]