from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from src.config.settings import get_settings
from src.video_agent.models.schemas import DemoVideoJobCreateResponse
from src.video_agent.services.analysis_runner import run_demo_video_analysis
from src.video_agent.services.video_job_store import JOB_STORE
from src.video_agent.utils import extract_json_object

logger = logging.getLogger(__name__)


def _run_job(
    job_id: str,
    video_path: Path,
    assignment_title: str,
    required_features: list[str] | None,
) -> None:
    settings = get_settings()
    try:
        JOB_STORE.update(job_id, status="running")
        raw = run_demo_video_analysis(
            video_path,
            assignment_title=assignment_title,
            required_features=required_features,
            settings=settings,
        )
        parsed: dict | None
        try:
            parsed = extract_json_object(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = None
        JOB_STORE.update(job_id, status="completed", raw_output=raw, parsed=parsed)
    except Exception as exc:
        logger.exception("Video analysis job %s failed", job_id)
        JOB_STORE.update(job_id, status="failed", error=str(exc))


def start_video_analysis_job(
    *,
    video_path: Path,
    assignment_title: str,
    required_features: list[str] | None,
) -> DemoVideoJobCreateResponse:
    job = JOB_STORE.create_job(video_path=str(video_path))

    thread = threading.Thread(
        target=_run_job,
        args=(job.job_id, video_path, assignment_title, required_features),
        daemon=True,
        name=f"video-analysis-{job.job_id}",
    )
    thread.start()

    return DemoVideoJobCreateResponse(job_id=job.job_id, status="pending")
