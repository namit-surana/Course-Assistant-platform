from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.orm import Session, selectinload

from src.api_ui.services.analysis_run_service import AnalysisRunService
from src.api_ui.services.run_store import AnalysisRunStore
from src.aws.s3_service import S3StorageService
from src.config.settings import Settings, get_settings
from src.db.models import AnalysisJob, FeedbackReport, FeedbackScore, Submission, SubmissionArtifact
from src.db.session import get_session_factory
from src.github_agent.phase1.models.schemas import AnalyzeRequest
from src.github_agent.phase1.services.context_builder import ContextBuilder
from src.github_agent.phase1.services.filter_service import FilterService
from src.github_agent.phase1.services.github_service import GitHubService
from src.github_agent.phase2.services.tree_analysis_service import create_tree_analysis_service
from src.github_agent.phase3.services.repository_analysis_service import create_repository_analysis_service
from src.ppt_agent.ppt_analyzer import analyze_ppt
from src.video_agent.video_analyzer import analyze_video


def process_analysis_job(job_id: str, settings: Settings | None = None) -> None:
    resolved_settings = settings or get_settings()
    session_factory = get_session_factory()
    with session_factory() as session:
        process_analysis_job_with_session(session, job_id, resolved_settings)


def process_analysis_job_with_session(
    session: Session,
    job_id: str,
    settings: Settings,
) -> None:
    job = session.get(
        AnalysisJob,
        job_id,
        options=[
            selectinload(AnalysisJob.submission).selectinload(Submission.artifacts),
        ],
    )
    if job is None:
        raise ValueError(f"Analysis job not found: {job_id}")

    submission = job.submission
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.attempts += 1
    job.started_at = now
    submission.status = "running"
    submission.error_message = None
    session.commit()

    try:
        raw_result = _run_submission_analysis(submission, settings)
        _save_feedback(session, submission, raw_result)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = None
        submission.status = "completed"
        submission.error_message = None
        session.commit()
    except Exception as exc:
        session.rollback()
        job = session.get(AnalysisJob, job_id)
        submission = session.get(Submission, submission.id)
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
        if submission is not None:
            submission.status = "failed"
            submission.error_message = str(exc)
        session.commit()
        raise


def _run_submission_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    result: dict[str, Any] = {"submission_id": submission.id, "team_name": submission.team_name}

    if settings.worker_enable_ppt_analysis:
        result["ppt"] = _run_ppt_analysis(submission, settings)
    else:
        result["ppt"] = {"skipped": True, "reason": "WORKER_ENABLE_PPT_ANALYSIS=false"}

    if settings.worker_enable_repository_analysis and submission.repo_url:
        result["repository"] = asyncio.run(_run_repository_analysis(submission, settings))
    elif submission.repo_url:
        result["repository"] = {
            "skipped": True,
            "reason": "WORKER_ENABLE_REPOSITORY_ANALYSIS=false",
        }

    if settings.worker_enable_video_analysis:
        result["video"] = _run_video_analysis(submission, settings)
    else:
        result["video"] = {"skipped": True, "reason": "WORKER_ENABLE_VIDEO_ANALYSIS=false"}


    return result


def _run_ppt_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    artifact = _first_artifact(submission.artifacts, {"ppt"})
    rubric = submission.rubric_snapshot or []
    if artifact is None:
        return {"skipped": True, "reason": "No PPT/PDF artifact was submitted."}
    if not rubric:
        return {"skipped": True, "reason": "No rubric criteria were submitted."}

    suffix = Path(artifact.file_name or artifact.object_key).suffix
    if suffix.lower() not in {".pptx", ".pdf"}:
        suffix = ".pptx"

    storage = S3StorageService(settings)
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as temp_file:
        storage.download_file(artifact.object_key, temp_file.name)
        return analyze_ppt(temp_file.name, rubric)


async def _run_repository_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    github_service = GitHubService(
        api_base_url=settings.github_api_base_url,
        request_timeout_seconds=settings.request_timeout_seconds,
        github_token=settings.github_token,
        cache_dir=settings.output_dir / "file_cache",
    )
    context_builder = ContextBuilder(output_dir=settings.output_dir)
    filter_service = FilterService(max_file_size_bytes=settings.max_file_size_bytes)
    tree_analysis_service = create_tree_analysis_service(
        settings,
        preview_fetcher=github_service.get_file_preview,
    )
    repository_analysis_service = create_repository_analysis_service(
        settings,
        preview_fetcher=github_service.get_file_preview,
    )
    run_service = AnalysisRunService(AnalysisRunStore())
    response = await run_service.run_inline(
        AnalyzeRequest(repo_url=submission.repo_url, branch=submission.branch),
        github_service=github_service,
        filter_service=filter_service,
        context_builder=context_builder,
        tree_analysis_service=tree_analysis_service,
        repository_analysis_service=repository_analysis_service,
    )
    return response.model_dump(mode="json")


def _run_video_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    artifact = _first_artifact(submission.artifacts, {"video"})
    rubric = submission.rubric_snapshot or []
    if artifact is None:
        return {"skipped": True, "reason": "No video artifact was submitted."}
    if not rubric:
        return {"skipped": True, "reason": "No rubric criteria were submitted."}

    suffix = Path(artifact.file_name or artifact.object_key).suffix or ".mp4"
    storage = S3StorageService(settings)
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as temp_file:
        storage.download_file(artifact.object_key, temp_file.name)
        return analyze_video(temp_file.name, rubric)


def _save_feedback(session: Session, submission: Submission, raw_result: dict[str, Any]) -> None:
    if submission.feedback_report is not None:
        session.delete(submission.feedback_report)
        session.flush()

    report = FeedbackReport(
        submission_id=submission.id,
        summary=_build_summary(raw_result),
        raw_result=raw_result,
    )
    session.add(report)
    session.flush()

    ppt_scores = raw_result.get("ppt", {}).get("criteria_scores", [])
    video_scores = raw_result.get("video", {}).get("criteria_scores", [])
    rubric_by_category = {
        item.get("category"): item
        for item in (submission.rubric_snapshot or [])
        if isinstance(item, dict)
    }
    for score_item in ppt_scores + video_scores:
        category = str(score_item.get("category", "")).strip()
        if not category:
            continue
        rubric_item = rubric_by_category.get(category, {})
        session.add(
            FeedbackScore(
                feedback_report_id=report.id,
                category=category,
                score=score_item.get("score", 0) or 0,
                max_score=rubric_item.get("max_score"),
                comment=score_item.get("comment"),
            )
        )


def _build_summary(raw_result: dict[str, Any]) -> str:
    ppt_summary = raw_result.get("ppt", {}).get("ppt_summary")
    video_summary = raw_result.get("video", {}).get("video_summary")
    repository_analysis = raw_result.get("repository", {}).get("repository_analysis", {})
    repo_summary = repository_analysis.get("executive_summary")
    parts = [part for part in [ppt_summary, video_summary, repo_summary] if part]
    if parts:
        return "\n\n".join(parts)
    return "Analysis completed. See raw_result for details."


def _first_artifact(
    artifacts: list[SubmissionArtifact],
    kinds: set[str],
) -> SubmissionArtifact | None:
    for artifact in artifacts:
        if artifact.kind in kinds:
            return artifact
    for artifact in artifacts:
        lower_path = PurePosixPath(artifact.object_key).name.lower()
        if lower_path.endswith((".pptx", ".pdf")):
            return artifact
    return None

