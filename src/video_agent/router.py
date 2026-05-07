from __future__ import annotations

import json
import re
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.config.settings import Settings, get_settings
from src.video_agent.models.schemas import DemoVideoJobCreateResponse, DemoVideoJobRecord
from src.video_agent.services.job_runner import start_video_analysis_job
from src.video_agent.services.video_job_store import JOB_STORE

router = APIRouter(prefix="/video-analysis", tags=["video-analysis"])

_ALLOWED_VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}


def _safe_filename(name: str) -> str:
    base = Path(name).name
    if not base or base in {".", ".."}:
        return "demo.bin"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", base)[:180]


@router.post("/jobs", response_model=DemoVideoJobCreateResponse)
async def enqueue_demo_video_analysis(
    file: UploadFile = File(...),
    assignment_title: str = Form(default="Course project demo"),
    required_features_json: str = Form(default="[]"),
    settings: Settings = Depends(get_settings),
) -> DemoVideoJobCreateResponse:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")

    try:
        required_features = json.loads(required_features_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="required_features_json must be a JSON array of strings.",
        ) from exc

    if not isinstance(required_features, list) or not all(isinstance(x, str) for x in required_features):
        raise HTTPException(
            status_code=400,
            detail="required_features_json must be a JSON array of strings.",
        )

    raw_name = file.filename or "demo.mp4"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in _ALLOWED_VIDEO_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type {suffix!r}. Allowed: {sorted(_ALLOWED_VIDEO_EXT)}",
        )

    content = await file.read()
    if len(content) > settings.video_max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Video exceeds max size of {settings.video_max_upload_bytes} bytes.",
        )

    upload_root = settings.video_upload_dir.resolve()
    upload_root.mkdir(parents=True, exist_ok=True)

    job_dir = upload_root / uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / _safe_filename(raw_name)
    dest.write_bytes(content)
    start_payload = start_video_analysis_job(
        video_path=dest,
        assignment_title=assignment_title,
        required_features=required_features,
    )
    return start_payload


@router.get("/jobs/{job_id}", response_model=DemoVideoJobRecord)
def get_demo_video_job(job_id: str) -> DemoVideoJobRecord:
    record = JOB_STORE.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return record
