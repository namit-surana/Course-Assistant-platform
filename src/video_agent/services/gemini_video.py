from __future__ import annotations

import logging
import time
from pathlib import Path

import google.generativeai as genai

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

    genai.configure(api_key=api_key)
    api_model = generative_model_name(model)
    video_file = genai.upload_file(path=str(path))
    deadline = time.time() + timeout_seconds

    try:
        while True:
            state_name = getattr(video_file.state, "name", str(video_file.state))
            if state_name == "ACTIVE":
                break
            if state_name == "FAILED":
                raise RuntimeError("Gemini failed to process the uploaded video file.")
            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for Gemini to activate the video file.")
            time.sleep(poll_seconds)
            video_file = genai.get_file(video_file.name)

        model_client = genai.GenerativeModel(api_model)
        response = model_client.generate_content([video_file, prompt])
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
            genai.delete_file(video_file.name)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.debug("Could not delete Gemini file %s: %s", video_file.name, exc)
