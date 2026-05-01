from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.voice_agent.models.schemas import VoiceTranscriptArtifact


class VoiceTranscriptStore:
    def __init__(self, output_dir: Path) -> None:
        self._base_dir = output_dir / "voice_transcripts"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, artifact: VoiceTranscriptArtifact) -> VoiceTranscriptArtifact:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        event_part = (artifact.event_id or "event").replace("/", "_")
        submission_part = (artifact.submission_id or "submission").replace("/", "_")
        file_path = self._base_dir / f"{event_part}__{submission_part}__{timestamp}.json"

        payload = artifact.model_dump(mode="json")
        payload["output_file"] = file_path.as_posix()
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return VoiceTranscriptArtifact.model_validate(payload)

