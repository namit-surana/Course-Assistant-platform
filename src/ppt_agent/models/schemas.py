from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PptCriterionScore(BaseModel):
    category: str
    score: float = Field(ge=0, le=5)
    comment: str


class PptAnalysisOutput(BaseModel):
    criteria_scores: list[PptCriterionScore]
    ppt_summary: str
    error: str | None = None


class PptArtifactKind(BaseModel):
    """Used if we later want to distinguish ppt vs pdf at the schema level."""

    kind: Literal["pptx", "pdf"]
