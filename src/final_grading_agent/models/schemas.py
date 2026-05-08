from typing import List, Optional

from pydantic import BaseModel, Field


class FinalCriterionGrade(BaseModel):
    criterion: str = Field(min_length=1)
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    reasoning: str = Field(min_length=1)
    evidence: List[str] = Field(default_factory=list)


class FinalGradingOutput(BaseModel):
    overall_score: float = Field(ge=0)
    overall_max_score: float = Field(gt=0)
    overall_reasoning: str = Field(min_length=1)
    criterion_grades: List[FinalCriterionGrade] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)
    key_improvements: List[str] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    confidence: Optional[str] = None
    limitations: Optional[str] = None

