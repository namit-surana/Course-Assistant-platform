from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


EventType = Literal["hackathon", "course", "custom"]
EventStatus = Literal["active", "draft", "completed"]


class EventCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: EventType = "hackathon"
    status: EventStatus = "active"
    description: str | None = None
    submission_deadline: date | None = None
    judging_deadline: date | None = None
    artifacts: list[str] = Field(default_factory=list)
    criteria_config: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    id: str
    name: str
    type: EventType
    status: EventStatus
    description: str | None
    submission_deadline: date | None
    judging_deadline: date | None
    artifacts: list[str]
    criteria_config: dict[str, Any]
    student_submit_url: str
    teams_total: int
    teams_evaluated: int
    created_at: datetime
    updated_at: datetime

