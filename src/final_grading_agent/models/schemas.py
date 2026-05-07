from __future__ import annotations

from pydantic import BaseModel, Field


class FinalCriterionGrade(BaseModel):
    criterion: str = Field(min_length=1)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    reasoning: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class FinalGradingOutput(BaseModel):
    overall_score: float = Field(ge=0)
    overall_max_score: float = Field(gt=0)
    overall_reasoning: str = Field(min_length=1)
    criterion_grades: list[FinalCriterionGrade] = Field(default_factory=list)
    key_strengths: list[str] = Field(default_factory=list)
    key_improvements: list[str] = Field(default_factory=list)
    evidence_summary: list[str] = Field(default_factory=list)
    confidence: str | None = None
    limitations: str | None = None

