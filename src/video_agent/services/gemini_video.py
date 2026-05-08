from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

from src.video_agent.utils import generative_model_name


logger = logging.getLogger(__name__)


def analyze_video_file(
    *,
    video_path: str,
    prompt: str,
    model: str,
    api_key: str | None,
    poll_seconds: float = 2.0,
    timeout_seconds: float = 600.0,
    on_uploaded: Callable[[], None] | None = None,
    on_active: Callable[[], None] | None = None,
    on_score_started: Callable[[], None] | None = None,
) -> str:
    """
    Upload a local video to Gemini, run multimodal generate_content, delete remote file.
    `model` may be `gemini-2.5-flash` or Crew-style `gemini/gemini-2.5-flash`.
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    client = genai.Client(api_key=api_key)
    api_model = generative_model_name(model)
    video_file = client.files.upload(
        file=str(path),
        config=types.UploadFileConfig(mime_type="video/mp4"),
    )
    if on_uploaded is not None:
        try:
            on_uploaded()
        except Exception:  # pragma: no cover - progress hook is best-effort
            logger.debug("on_uploaded hook raised", exc_info=True)
    deadline = time.time() + timeout_seconds

    try:
        while True:
            state_name = str(getattr(getattr(video_file, "state", None), "name", "")).upper()
            if state_name.endswith("ACTIVE"):
                break
            if state_name.endswith("FAILED"):
                raise RuntimeError("Gemini failed to process the uploaded video file.")
            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for Gemini to activate the video file.")
            time.sleep(poll_seconds)
            video_name = getattr(video_file, "name", None)
            if not video_name:
                raise RuntimeError("Gemini uploaded file name missing; cannot poll state.")
            video_file = client.files.get(name=video_name)

        if on_active is not None:
            try:
                on_active()
            except Exception:  # pragma: no cover
                logger.debug("on_active hook raised", exc_info=True)

        if on_score_started is not None:
            try:
                on_score_started()
            except Exception:  # pragma: no cover
                logger.debug("on_score_started hook raised", exc_info=True)

        response = client.models.generate_content(
            model=api_model,
            contents=[video_file, prompt],
        )
        text = getattr(response, "text", None)
        if text:
            return text
        if getattr(response, "candidates", None):
            parts: list[str] = []
            for candidate in response.candidates:
                content = getattr(candidate, "content", None)
                if content and getattr(content, "parts", None):
                    for part in content.parts:
                        if getattr(part, "text", None):
                            parts.append(part.text)
            if parts:
                return "\n".join(parts)
        raise RuntimeError("Gemini returned an empty response for the video.")
    finally:
        try:
            video_name = getattr(video_file, "name", None)
            if video_name:
                client.files.delete(name=video_name)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.debug("Could not delete Gemini file %s: %s", getattr(video_file, "name", "?"), exc)
