from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class VoiceTranscriptSegment(BaseModel):
    text: str
    start: float | None = None
    end: float | None = None


class VoiceTranscriptArtifact(BaseModel):
    session_id: str
    event_id: str | None = None
    submission_id: str | None = None
    full_transcript: str = ""
    segments: list[VoiceTranscriptSegment] = Field(default_factory=list)
    provider: str = "elevenlabs"
    model: str = "scribe_v2_realtime"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_file: str | None = None

    model_config = ConfigDict(json_encoders={Path: str})

