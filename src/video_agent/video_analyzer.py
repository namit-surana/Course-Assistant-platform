import json
import mimetypes
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from google import genai
from google.genai import types

from src.config.settings import get_settings
from .models import (
    CriterionScore,
    LargeVideoDecision,
    LargeVideoPrompt,
    RubricCriterion,
    VideoAnalysisMode,
    VideoAnalysisResult,
)
from .prompts import build_video_analysis_prompt
from .exceptions import (
    LargeVideoConfirmationRequired,
    UnsupportedVideoSourceError,
    VideoFileNotFoundError,
)

settings = get_settings()


DEFAULT_LARGE_VIDEO_THRESHOLD_MB = 100
DEFAULT_MAX_POLL_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 5

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
    ".m4v",
}


def analyze_video(
    video_source: str,
    rubric_criteria: list[dict[str, Any]],
    *,
    decision: LargeVideoDecision = LargeVideoDecision.REQUIRE_CONFIRMATION,
    analysis_mode: VideoAnalysisMode | None = None,
) -> dict[str, Any]:
    """
    Analyze a project demo video against rubric criteria.

    Supports:
    - local video file path
    - direct public video URL / S3 presigned URL
    - best-effort public video URL analysis for non-direct links
    - large-file confirmation before expensive full-video analysis

    For large videos:
    - decision=REQUIRE_CONFIRMATION returns a prompt object instead of analyzing
    - decision=PROCEED_FULL_VIDEO uploads full video to Gemini Files API
    - decision=PROCEED_TRANSCRIPTION_ONLY extracts/transcribes audio and grades transcript only

    Frontend can call this once, receive requires_confirmation=True,
    show the warning UI, then call again with the user's selected decision.
    """
    try:
        criteria = _validate_rubric(rubric_criteria)

        # Keeping this for future frontend/API usage.
        # This can be stored in DB, sent back to frontend, used in logs,
        # or used by the worker to show which mode was finally selected.
        selected_mode = analysis_mode or _mode_from_decision(decision)

        source_kind = _detect_source_kind(video_source)

        if source_kind == "local_file":
            file_path = Path(video_source)
            _validate_local_video(file_path)

            size_bytes = file_path.stat().st_size
            large_threshold_bytes = _get_large_video_threshold_bytes()

            if size_bytes >= large_threshold_bytes and decision == LargeVideoDecision.REQUIRE_CONFIRMATION:
                prompt = _build_large_video_prompt(size_bytes, large_threshold_bytes)
                data = prompt.model_dump()
                data["selected_analysis_mode"] = selected_mode.value
                return data

            if decision == LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY:
                return _analyze_local_video_by_transcription(file_path, criteria).model_dump()

            return _analyze_local_video_with_gemini_files(file_path, criteria).model_dump()

        if source_kind == "url":
            large_threshold_bytes = _get_large_video_threshold_bytes()
            remote_size_bytes = _get_remote_content_length(video_source)

            if (
                remote_size_bytes is not None
                and remote_size_bytes >= large_threshold_bytes
                and decision == LargeVideoDecision.REQUIRE_CONFIRMATION
            ):
                prompt = _build_large_video_prompt(remote_size_bytes, large_threshold_bytes)
                data = prompt.model_dump()
                data["selected_analysis_mode"] = selected_mode.value
                data["metadata"] = {
                    "source_type": "url",
                    "video_url": video_source,
                    "remote_content_length_detected": True,
                }
                return data

            # Direct video URLs and S3 presigned URLs are safer when downloaded first
            # and uploaded through Gemini Files API instead of passing the URL directly.
            if _is_direct_video_url(video_source):
                temp_path: Path | None = None
                try:
                    temp_path = _download_url_to_temp_file(video_source)
                    _validate_local_video(temp_path)

                    size_bytes = temp_path.stat().st_size
                    if size_bytes >= large_threshold_bytes and decision == LargeVideoDecision.REQUIRE_CONFIRMATION:
                        prompt = _build_large_video_prompt(size_bytes, large_threshold_bytes)
                        data = prompt.model_dump()
                        data["selected_analysis_mode"] = selected_mode.value
                        data["metadata"] = {
                            "source_type": "url",
                            "video_url": video_source,
                            "remote_content_length_detected": remote_size_bytes is not None,
                        }
                        return data

                    if decision == LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY:
                        return _analyze_local_video_by_transcription(
                            temp_path,
                            criteria,
                            metadata={
                                "source_type": "url",
                                "video_url": video_source,
                                "downloaded_for_analysis": True,
                            },
                        ).model_dump()

                    return _analyze_local_video_with_gemini_files(
                        temp_path,
                        criteria,
                        metadata={
                            "source_type": "url",
                            "video_url": video_source,
                            "downloaded_for_analysis": True,
                        },
                    ).model_dump()

                finally:
                    if temp_path and temp_path.exists():
                        temp_path.unlink(missing_ok=True)

            if decision == LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY:
                return {
                    "criteria_scores": [],
                    "video_summary": "",
                    "analysis_mode": VideoAnalysisMode.TRANSCRIPTION_ONLY.value,
                    "warnings": [
                        "Transcription-only mode is supported for local files and direct downloadable video URLs only. "
                        "This URL does not look like a direct video file."
                    ],
                    "error": "Unsupported transcription-only URL mode",
                }

            # Best-effort fallback for non-direct URLs, such as public video links.
            # Some URLs may not be supported by Gemini. For app-uploaded/S3 videos,
            # prefer direct download + Gemini Files API path above.
            return _analyze_video_url_with_gemini(video_source, criteria).model_dump()

        raise UnsupportedVideoSourceError(f"Unsupported video source: {video_source}")

    except LargeVideoConfirmationRequired as exc:
        return {"requires_confirmation": True, "error": str(exc)}
    except Exception as exc:
        return {
            "criteria_scores": [],
            "video_summary": "",
            "analysis_mode": (analysis_mode or VideoAnalysisMode.FULL_VIDEO).value,
            "warnings": [],
            "error": f"Video analysis failed: {str(exc)}",
        }


def _validate_rubric(rubric_criteria: list[dict[str, Any]]) -> list[RubricCriterion]:
    if not rubric_criteria:
        raise ValueError("rubric_criteria cannot be empty")

    return [RubricCriterion(**item) for item in rubric_criteria]


def _detect_source_kind(video_source: str) -> str:
    source = video_source.strip()

    if source.startswith(("http://", "https://")):
        return "url"

    return "local_file"


def _validate_local_video(file_path: Path) -> None:
    if not file_path.exists():
        raise VideoFileNotFoundError(f"Video file not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Video source is not a file: {file_path}")

    suffix = file_path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(str(file_path))

    has_valid_extension = suffix in ALLOWED_VIDEO_EXTENSIONS
    has_valid_mime = bool(mime_type and mime_type.startswith("video/"))

    if not has_valid_extension and not has_valid_mime:
        raise ValueError(
            f"Unsupported video file type. Extension={suffix or 'unknown'}, "
            f"MIME={mime_type or 'unknown'}."
        )


def _mode_from_decision(decision: LargeVideoDecision) -> VideoAnalysisMode:
    """
    Maps the frontend/user decision to the analyzer's internal mode.

    Kept separate intentionally for future frontend/worker use:
    - can be logged
    - can be stored in DB
    - can be returned to frontend
    - can help show whether analysis used full video or transcript-only mode
    """
    if decision == LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY:
        return VideoAnalysisMode.TRANSCRIPTION_ONLY

    return VideoAnalysisMode.FULL_VIDEO


def _get_large_video_threshold_bytes() -> int:
    threshold_mb = getattr(
        settings,
        "video_large_file_threshold_mb",
        DEFAULT_LARGE_VIDEO_THRESHOLD_MB,
    )
    return int(float(threshold_mb) * 1024 * 1024)


def _build_large_video_prompt(
    file_size_bytes: int,
    threshold_bytes: int,
) -> LargeVideoPrompt:
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    threshold_mb = round(threshold_bytes / (1024 * 1024), 2)

    return LargeVideoPrompt(
        file_size_bytes=file_size_bytes,
        file_size_mb=file_size_mb,
        threshold_mb=threshold_mb,
        message=(
            f"This video is {file_size_mb} MB, which is larger than the configured "
            f"{threshold_mb} MB threshold. Full Gemini video analysis may cost more because "
            "the model processes visual frames and audio. Choose how you want to proceed."
        ),
        options=[
            {
                "id": LargeVideoDecision.PROCEED_FULL_VIDEO.value,
                "label": "Proceed with full video analysis",
                "description": (
                    "Best accuracy. Gemini evaluates visuals, screen recording, slides, "
                    "demo flow, and audio. Higher cost for large videos."
                ),
            },
            {
                "id": LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY.value,
                "label": "Proceed with transcription-only analysis",
                "description": (
                    "Lower-cost fallback. Extracts/transcribes audio and grades only spoken content. "
                    "Visual demo quality may not be evaluated."
                ),
            },
        ],
    )


def _analyze_local_video_with_gemini_files(
    file_path: Path,
    rubric_criteria: list[RubricCriterion],
    metadata: dict[str, Any] | None = None,
) -> VideoAnalysisResult:
    client = _get_gemini_client()

    mime_type, _ = mimetypes.guess_type(str(file_path))

    uploaded_file = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(
            mime_type=mime_type or "video/mp4",
        ),
    )
    uploaded_file = _wait_for_file_active(client, uploaded_file)

    prompt = build_video_analysis_prompt(
        rubric_criteria=rubric_criteria,
        analysis_mode=VideoAnalysisMode.FULL_VIDEO,
    )

    response = client.models.generate_content(
        model=_get_video_model(),
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    parsed = _extract_json(response.text)

    result_metadata = {
        "source_type": "local_file",
        "file_name": file_path.name,
        "file_size_bytes": file_path.stat().st_size,
        "gemini_file_uri": getattr(uploaded_file, "uri", None),
    }
    if metadata:
        result_metadata.update(metadata)

    return _normalize_result(
        parsed,
        rubric_criteria,
        analysis_mode=VideoAnalysisMode.FULL_VIDEO,
        metadata=result_metadata,
    )


def _analyze_video_url_with_gemini(
    video_url: str,
    rubric_criteria: list[RubricCriterion],
) -> VideoAnalysisResult:
    client = _get_gemini_client()

    prompt = build_video_analysis_prompt(
        rubric_criteria=rubric_criteria,
        analysis_mode=VideoAnalysisMode.FULL_VIDEO,
    )

    response = client.models.generate_content(
        model=_get_video_model(),
        contents=types.Content(
            parts=[
                types.Part(
                    file_data=types.FileData(
                        file_uri=video_url,
                    )
                ),
                types.Part(text=prompt),
            ]
        ),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    parsed = _extract_json(response.text)

    return _normalize_result(
        parsed,
        rubric_criteria,
        analysis_mode=VideoAnalysisMode.FULL_VIDEO,
        metadata={
            "source_type": "url",
            "video_url": video_url,
            "url_analysis_mode": "direct_gemini_url_best_effort",
        },
    )


def _analyze_local_video_by_transcription(
    file_path: Path,
    rubric_criteria: list[RubricCriterion],
    metadata: dict[str, Any] | None = None,
) -> VideoAnalysisResult:
    transcript = _extract_transcript_from_video(file_path)

    if not transcript.strip():
        raise ValueError("Could not extract transcript from video.")

    client = _get_gemini_client()

    prompt = build_video_analysis_prompt(
        rubric_criteria=rubric_criteria,
        analysis_mode=VideoAnalysisMode.TRANSCRIPTION_ONLY,
    )

    transcript_prompt = f"""
{prompt}

Transcript:
{transcript}
""".strip()

    response = client.models.generate_content(
        model=_get_text_model(),
        contents=transcript_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    parsed = _extract_json(response.text)

    result_metadata = {
        "source_type": "local_file",
        "file_name": file_path.name,
        "file_size_bytes": file_path.stat().st_size,
    }
    if metadata:
        result_metadata.update(metadata)

    result = _normalize_result(
        parsed,
        rubric_criteria,
        analysis_mode=VideoAnalysisMode.TRANSCRIPTION_ONLY,
        metadata=result_metadata,
    )

    result.warnings.append(
        "This result used transcription-only analysis. Visual demo quality, UI behavior, "
        "slides shown on screen, and code walkthrough details may not be fully evaluated."
    )

    return result


def _extract_transcript_from_video(file_path: Path) -> str:
    """
    Lower-cost fallback.

    This extracts audio with ffmpeg and asks Gemini to transcribe/summarize the audio.
    Requires ffmpeg in the runtime image.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_wav:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(file_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            tmp_wav.name,
        ]

        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        client = _get_gemini_client()

        uploaded_audio = client.files.upload(
            file=tmp_wav.name,
            config=types.UploadFileConfig(
                mime_type="audio/wav",
            ),
        )
        uploaded_audio = _wait_for_file_active(client, uploaded_audio)

        response = client.models.generate_content(
            model=_get_text_model(),
            contents=[
                uploaded_audio,
                (
                    "Transcribe the spoken content from this audio as accurately as possible. "
                    "Also include short notes for unclear sections. Return plain text only."
                ),
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        return response.text or ""


def _wait_for_file_active(client: genai.Client, uploaded_file: Any) -> Any:
    """
    Gemini Files API may need processing time for uploaded media.
    Poll until ACTIVE or fail fast.
    """
    max_poll_seconds = int(
        getattr(settings, "video_file_processing_timeout_seconds", DEFAULT_MAX_POLL_SECONDS)
    )
    poll_interval = int(
        getattr(settings, "video_file_poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
    )

    start_time = time.time()
    file_name = getattr(uploaded_file, "name", None)

    while True:
        state = _file_state_name(getattr(uploaded_file, "state", None))

        if state == "ACTIVE" or state.endswith("ACTIVE"):
            return uploaded_file

        if state == "FAILED" or state.endswith("FAILED"):
            raise RuntimeError("Gemini file processing failed.")

        if time.time() - start_time > max_poll_seconds:
            raise TimeoutError("Timed out waiting for Gemini file processing.")

        time.sleep(poll_interval)

        if not file_name:
            raise RuntimeError("Gemini uploaded file name is missing; cannot poll processing state.")

        uploaded_file = client.files.get(name=file_name)


def _file_state_name(state: Any) -> str:
    if state is None:
        return ""

    name = getattr(state, "name", None)
    return str(name or state).upper()


def _get_gemini_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    return genai.Client(api_key=api_key)


def _get_video_model() -> str:
    return settings.video_analysis_model


def _get_text_model() -> str:
    return settings.video_transcription_model


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    obj = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if obj:
        return json.loads(obj.group(0))

    raise ValueError("No valid JSON object found in Gemini response.")


def _normalize_result(
    raw_result: dict[str, Any],
    rubric_criteria: list[RubricCriterion],
    analysis_mode: VideoAnalysisMode,
    metadata: dict[str, Any] | None = None,
) -> VideoAnalysisResult:
    raw_scores = raw_result.get("criteria_scores", [])
    normalized_scores: list[CriterionScore] = []

    for criterion in rubric_criteria:
        matched = next(
            (
                item
                for item in raw_scores
                if str(item.get("category", "")).strip().lower()
                == criterion.category.strip().lower()
            ),
            None,
        )

        if not matched:
            normalized_scores.append(
                CriterionScore(
                    category=criterion.category,
                    score=0.0,
                    max_score=criterion.max_score,
                    comment="No evaluation was returned for this criterion.",
                    evidence="Missing from model response.",
                )
            )
            continue

        raw_score = matched.get("score", 0.0)

        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0

        score = max(0.0, min(score, criterion.max_score))

        normalized_scores.append(
            CriterionScore(
                category=criterion.category,
                score=score,
                max_score=criterion.max_score,
                comment=str(matched.get("comment", "")).strip(),
                evidence=str(matched.get("evidence", "")).strip(),
            )
        )

    total_score = sum(item.score for item in normalized_scores)
    max_total_score = sum(item.max_score for item in normalized_scores)

    return VideoAnalysisResult(
        criteria_scores=normalized_scores,
        video_summary=str(raw_result.get("video_summary", "")).strip(),
        analysis_mode=analysis_mode,
        total_score=total_score,
        max_total_score=max_total_score,
        warnings=list(raw_result.get("warnings", [])),
        metadata=metadata or {},
    )


def _is_direct_video_url(video_url: str) -> bool:
    """
    Returns True for direct downloadable video URLs, including many S3 presigned URLs.

    This intentionally uses both extension and Content-Type checks because presigned URLs
    may have query parameters and may not always expose clean file names.
    """
    parsed = urlparse(video_url)
    suffix = Path(parsed.path).suffix.lower()

    if suffix in ALLOWED_VIDEO_EXTENSIONS:
        return True

    content_type = _get_remote_content_type(video_url)
    return bool(content_type and content_type.startswith("video/"))


def _get_remote_content_length(video_url: str) -> int | None:
    try:
        request = urllib.request.Request(video_url, method="HEAD")
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")

        if content_length:
            return int(content_length)

    except Exception:
        return None

    return None


def _get_remote_content_type(video_url: str) -> str | None:
    try:
        request = urllib.request.Request(video_url, method="HEAD")
        with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
            content_type = response.headers.get("Content-Type")

        if content_type:
            return content_type.split(";")[0].strip().lower()

    except Exception:
        return None

    return None


def _download_url_to_temp_file(video_url: str) -> Path:
    parsed = urlparse(video_url)
    suffix = Path(parsed.path).suffix.lower()

    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        suffix = ".mp4"

    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_path = Path(temp_file.name)

    try:
        with temp_file:
            request = urllib.request.Request(video_url, method="GET")
            with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    temp_file.write(chunk)

        return temp_path

    except Exception:
        temp_path.unlink(missing_ok=True)
        raise