from __future__ import annotations

import asyncio
import json
from urllib.parse import urlencode

from fastapi import WebSocket, WebSocketDisconnect
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from src.voice_agent.models.schemas import VoiceTranscriptArtifact, VoiceTranscriptSegment
from src.voice_agent.services.transcript_store import VoiceTranscriptStore


class VoiceRealtimeBridge:
    def __init__(
        self,
        *,
        api_key: str,
        transcript_store: VoiceTranscriptStore,
        base_ws_url: str = "wss://api.elevenlabs.io",
    ) -> None:
        self.api_key = api_key
        self.base_ws_url = base_ws_url.rstrip("/")
        self.transcript_store = transcript_store

    async def run(
        self,
        *,
        client_socket: WebSocket,
        event_id: str | None = None,
        submission_id: str | None = None,
        language_code: str = "eng",
    ) -> None:
        await client_socket.accept()
        query = urlencode(
            {
                "model_id": "scribe_v2_realtime",
                "audio_format": "pcm_16000",
                "commit_strategy": "vad",
                "include_timestamps": "true",
                "language_code": language_code,
            }
        )
        provider_url = f"{self.base_ws_url}/v1/speech-to-text/realtime?{query}"
        headers = {"xi-api-key": self.api_key}
        segments: list[VoiceTranscriptSegment] = []
        segment_index_by_text: dict[str, int] = {}
        full_transcript_parts: list[str] = []
        provider_session_id: str | None = None

        async with ws_connect(provider_url, extra_headers=headers) as provider_socket:
            async def forward_client_audio() -> None:
                while True:
                    try:
                        message = await client_socket.receive_json()
                    except WebSocketDisconnect:
                        return
                    msg_type = message.get("type")
                    if msg_type == "audio_chunk":
                        payload = {
                            "message_type": "input_audio_chunk",
                            "audio_base_64": message.get("audio_base64", ""),
                            "commit": bool(message.get("commit", False)),
                            "sample_rate": int(message.get("sample_rate", 16000)),
                        }
                        try:
                            await provider_socket.send(json.dumps(payload))
                        except ConnectionClosed:
                            return
                    elif msg_type == "commit":
                        payload = {
                            "message_type": "input_audio_chunk",
                            "audio_base_64": "",
                            "commit": True,
                            "sample_rate": int(message.get("sample_rate", 16000)),
                        }
                        try:
                            await provider_socket.send(json.dumps(payload))
                        except ConnectionClosed:
                            return
                    elif msg_type == "stop":
                        try:
                            await provider_socket.close()
                        except ConnectionClosed:
                            pass
                        return

            async def forward_provider_events() -> None:
                nonlocal provider_session_id
                try:
                    async for raw_event in provider_socket:
                        parsed = json.loads(raw_event)
                        message_type = parsed.get("message_type")

                        if message_type == "session_started":
                            provider_session_id = parsed.get("session_id")

                        if message_type in {
                            "committed_transcript",
                            "committed_transcript_with_timestamps",
                        }:
                            text = str(parsed.get("text", "")).strip()
                            if text:
                                segment = VoiceTranscriptSegment(text=text)
                                words = parsed.get("words") or []
                                if words:
                                    start = words[0].get("start")
                                    end = words[-1].get("end")
                                    segment.start = float(start) if start is not None else None
                                    segment.end = float(end) if end is not None else None
                                normalized = text.casefold()
                                existing_index = segment_index_by_text.get(normalized)
                                if existing_index is None:
                                    segments.append(segment)
                                    segment_index_by_text[normalized] = len(segments) - 1
                                    full_transcript_parts.append(text)
                                else:
                                    existing = segments[existing_index]
                                    # Prefer timestamped variant if it arrives later.
                                    if existing.start is None and segment.start is not None:
                                        segments[existing_index] = segment

                        try:
                            await client_socket.send_json(parsed)
                        except WebSocketDisconnect:
                            return
                except ConnectionClosed:
                    # Provider-side close after stop is expected.
                    return

            tasks = [
                asyncio.create_task(forward_client_audio()),
                asyncio.create_task(forward_provider_events()),
            ]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                try:
                    task.result()
                except ConnectionClosed:
                    # Normal provider-side close path.
                    pass

        artifact = VoiceTranscriptArtifact(
            session_id=provider_session_id or "unknown-session",
            event_id=event_id,
            submission_id=submission_id,
            full_transcript=" ".join(full_transcript_parts).strip(),
            segments=segments,
        )
        saved = self.transcript_store.save(artifact)
        try:
            await client_socket.send_json(
                {
                    "message_type": "session_saved",
                    "artifact": saved.model_dump(mode="json"),
                }
            )
        except WebSocketDisconnect:
            return
