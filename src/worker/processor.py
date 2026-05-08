from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from contextlib import AbstractContextManager, nullcontext
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.api_ui.services.analysis_run_service import AnalysisRunService
from src.api_ui.services.run_store import AnalysisRunStore
from src.aws.sqs_service import SqsQueueService
from src.aws.s3_service import S3StorageService
from src.config.settings import Settings, get_settings
from src.db.models import AnalysisJob, EvaluationEvent, FeedbackReport, FeedbackScore, Submission, SubmissionArtifact
from src.final_grading_agent.crew.final_grading_crew import run_final_grading
from src.db.session import get_session_factory
from src.github_agent.phase1.models.schemas import AnalyzeRequest
from src.github_agent.phase1.services.context_builder import ContextBuilder
from src.github_agent.phase1.services.filter_service import FilterService
from src.github_agent.phase1.services.github_service import GitHubService
from src.github_agent.phase2.services.tree_analysis_service import create_tree_analysis_service
from src.github_agent.phase3.services.repository_analysis_service import create_repository_analysis_service
from src.ppt_agent.ppt_analyzer import analyze_ppt, builtin_ppt_rubric_by_category
from src.video_agent.services.analysis_runner import run_demo_video_analysis

logger = logging.getLogger(__name__)


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
    submission_id = submission.id
    trigger_job_type = (job.job_type or "").strip()
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.attempts += 1
    job.started_at = now
    job.result_json = None
    submission.status = "running"
    submission.error_message = None
    session.commit()

    try:
        raw_result = _run_job_by_type(session, job, submission, settings)
        _raise_if_no_successful_analysis(raw_result)
        _save_feedback(session, submission, raw_result)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.result_json = raw_result
        job.error_message = None
        _maybe_enqueue_final_grading_job(
            session,
            submission_id,
            settings,
            triggering_job_type=trigger_job_type,
        )
        _refresh_submission_status(session, submission_id)
        session.commit()
    except Exception as exc:
        session.rollback()
        job = session.get(AnalysisJob, job_id)
        submission = session.get(Submission, submission_id)
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.result_json = {"error": str(exc)}
            job.completed_at = datetime.now(timezone.utc)
        if submission is not None:
            _maybe_enqueue_final_grading_job(
                session,
                submission_id,
                settings,
                triggering_job_type=trigger_job_type,
            )
            _refresh_submission_status(session, submission_id)
        session.commit()
        raise


def _run_submission_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    async def _run_all() -> dict[str, Any]:
        result: dict[str, Any] = {"submission_id": submission.id, "team_name": submission.team_name}

        tasks: dict[str, asyncio.Task[Any]] = {}

        if settings.worker_enable_ppt_analysis:
            tasks["ppt"] = asyncio.create_task(
                asyncio.to_thread(_run_ppt_analysis, submission, settings),
                name="submission:ppt",
            )
        else:
            result["ppt"] = {"skipped": True, "reason": "WORKER_ENABLE_PPT_ANALYSIS=false"}

        if submission.repo_url and settings.worker_enable_repository_analysis:
            tasks["repository"] = asyncio.create_task(
                _run_repository_analysis(submission, settings),
                name="submission:repository",
            )
        elif submission.repo_url:
            result["repository"] = {"skipped": True, "reason": "WORKER_ENABLE_REPOSITORY_ANALYSIS=false"}

        if settings.worker_enable_video_analysis:
            # Demo video analysis is included in submission_analysis when a video artifact exists.
            tasks["video"] = asyncio.create_task(
                asyncio.to_thread(_run_video_analysis, submission, None, settings),
                name="submission:video",
            )
        else:
            result["video"] = {"skipped": True, "reason": "WORKER_ENABLE_VIDEO_ANALYSIS=false"}

        if not tasks:
            return result

        finished = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for key, value in zip(tasks.keys(), finished):
            if isinstance(value, Exception):
                result[key] = {"error": str(value)}
            else:
                result[key] = value

        return result

    return asyncio.run(_run_all())


def _run_job_by_type(
    session: Session,
    job: AnalysisJob,
    submission: Submission,
    settings: Settings,
) -> dict[str, Any]:
    job_type = (job.job_type or "submission_analysis").strip()
    if job_type == "submission_analysis":
        return _run_submission_analysis(submission, settings)
    if job_type == "git_analysis":
        if not submission.repo_url:
            return {"repository": {"skipped": True, "reason": "No repository URL submitted."}}
        return {"repository": asyncio.run(_run_repository_analysis(submission, settings))}
    if job_type == "ppt_analysis":
        return {"ppt": _run_ppt_analysis(submission, settings)}
    if job_type == "video_analysis":
        if not settings.worker_enable_video_analysis:
            return {"video": {"skipped": True, "reason": "WORKER_ENABLE_VIDEO_ANALYSIS=false"}}
        return {"video": _run_video_analysis(submission, job, settings)}
    if job_type == "final_grading_analysis":
        return {"final_grading": _run_final_grading_analysis(session, submission, settings)}
    raise RuntimeError(f"Unsupported job_type: {job_type}")


def _run_final_grading_analysis(
    session: Session,
    submission: Submission,
    settings: Settings,
    *,
    crew_context: AbstractContextManager[Any] | None = None,
    on_context_ready: Callable[[], None] | None = None,
) -> dict[str, Any]:
    event = session.get(EvaluationEvent, submission.event_id) if submission.event_id else None
    criteria_config = event.criteria_config if event and event.criteria_config else {}
    normalized_criteria_config = _normalize_criteria_config_for_final_grading(criteria_config, submission)
    component_results = _latest_component_results_for_submission(session, submission.id)
    submission_context = {
        "submission_id": submission.id,
        "team_name": submission.team_name,
        "repo_url": submission.repo_url,
        "branch": submission.branch,
        "artifacts": [
            {
                "kind": artifact.kind,
                "file_name": artifact.file_name,
                "object_key": artifact.object_key,
            }
            for artifact in submission.artifacts
        ],
    }

    if on_context_ready is not None:
        on_context_ready()
    ctx = crew_context if crew_context is not None else nullcontext()
    with ctx:
        final_report = run_final_grading(
            model=settings.final_grading_model,
            gemini_api_key=settings.GEMINI_API_KEY,
            submission_context_json=json.dumps(submission_context, default=str),
            criteria_config_json=json.dumps(normalized_criteria_config, default=str),
            repository_result_json=json.dumps(component_results["repository"], default=str),
            ppt_result_json=json.dumps(component_results["ppt"], default=str),
            video_result_json=json.dumps(component_results["video"], default=str),
        )
    return final_report.model_dump(mode="json")


def _normalize_criteria_config_for_final_grading(
    criteria_config: dict[str, Any],
    submission: Submission,
) -> dict[str, Any]:
    if not isinstance(criteria_config, dict):
        return {}

    raw_criteria = criteria_config.get("criteria", criteria_config)
    if not isinstance(raw_criteria, dict):
        return {"criteria": {}, "artifacts": []}

    configured_artifacts = criteria_config.get("artifacts")
    configured_artifact_set = {
        str(artifact)
        for artifact in (configured_artifacts if isinstance(configured_artifacts, list) else [])
        if isinstance(artifact, str) and artifact
    }
    submission_artifact_set = {
        artifact.kind
        for artifact in submission.artifacts
        if getattr(artifact, "kind", None)
    }
    allowed_artifacts = configured_artifact_set or submission_artifact_set

    normalized_criteria: dict[str, Any] = {}
    for criterion_id, state in raw_criteria.items():
        if not isinstance(state, dict):
            continue
        if not state.get("selected", False):
            continue
        weight = state.get("weight")
        try:
            if float(weight or 0) <= 0:
                continue
        except (TypeError, ValueError):
            continue

        criterion_id_str = str(criterion_id)
        criterion_artifact = state.get("artifactId")
        if isinstance(criterion_artifact, str) and criterion_artifact in allowed_artifacts:
            normalized_criteria[criterion_id_str] = state

    return {
        "criteria": normalized_criteria,
        "artifacts": sorted(allowed_artifacts),
    }


def _run_ppt_analysis(submission: Submission, settings: Settings) -> dict[str, Any]:
    artifact = _first_artifact(submission.artifacts, {"ppt"})
    if artifact is None:
        return {"skipped": True, "reason": "No PPT/PDF artifact was submitted."}

    suffix = Path(artifact.file_name or artifact.object_key).suffix
    if suffix.lower() not in {".pptx", ".pdf"}:
        suffix = ".pptx"

    storage = S3StorageService(settings)
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as temp_file:
        storage.download_file(artifact.object_key, temp_file.name)
        return analyze_ppt(temp_file.name)


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


def _run_video_analysis(submission: Submission, _job: AnalysisJob | None, settings: Settings) -> dict[str, Any]:
    # job_payload is ignored: demo analysis uses only the built-in video rubric (no prof assignment/features).
    artifact = _first_artifact(submission.artifacts, {"video"})
    if artifact is None:
        return {"skipped": True, "reason": "No video artifact was submitted."}
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not configured.")

    assignment_title = "Course project demo"
    required_features: list[str] = []

    suffix = Path(artifact.file_name or artifact.object_key).suffix or ".mp4"
    storage = S3StorageService(settings)
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as temp_file:
        storage.download_file(artifact.object_key, temp_file.name)
        raw, parsed = run_demo_video_analysis(
            Path(temp_file.name),
            assignment_title=assignment_title,
            required_features=required_features,
            settings=settings,
        )

    return {"raw_output": raw, "parsed": parsed}


def _save_feedback(session: Session, submission: Submission, raw_result: dict[str, Any]) -> None:
    report = submission.feedback_report
    if report is None:
        report = FeedbackReport(
            submission_id=submission.id,
            summary=None,
            raw_result={},
        )
        session.add(report)
        session.flush()

    merged_raw_result = _merge_feedback_raw_result(report.raw_result, raw_result)
    report.raw_result = merged_raw_result
    report.summary = _build_summary(merged_raw_result)
    session.add(report)
    session.flush()

    if "ppt" in raw_result:
        _replace_ppt_scores(session, report, raw_result["ppt"])


def _merge_feedback_raw_result(
    existing_raw_result: dict[str, Any] | None,
    incoming_raw_result: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing_raw_result or {})
    merged.update(incoming_raw_result)
    return merged


def _replace_ppt_scores(session: Session, report: FeedbackReport, ppt_result: Any) -> None:
    rubric_by_category = builtin_ppt_rubric_by_category()
    ppt_categories = set(rubric_by_category.keys())

    for existing_score in list(report.scores):
        if existing_score.category in ppt_categories:
            session.delete(existing_score)
    session.flush()

    if not isinstance(ppt_result, dict):
        return

    ppt_scores = ppt_result.get("criteria_scores", [])
    for score_item in ppt_scores:
        if not isinstance(score_item, dict):
            continue
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


def _refresh_submission_status(session: Session, submission_id: str) -> None:
    submission = session.get(Submission, submission_id)
    if submission is None:
        return

    jobs = list(
        session.scalars(
            select(AnalysisJob)
            .where(AnalysisJob.submission_id == submission_id)
            .order_by(AnalysisJob.updated_at.desc())
        )
    )
    if not jobs:
        submission.status = "submitted"
        submission.error_message = None
        return

    statuses = {job.status for job in jobs}
    if "running" in statuses:
        submission.status = "running"
        submission.error_message = None
        return
    if "queued" in statuses:
        submission.status = "queued"
        submission.error_message = None
        return
    if "failed" in statuses:
        submission.status = "failed"
        latest_failed = next((job for job in jobs if job.status == "failed"), None)
        submission.error_message = (
            latest_failed.error_message
            if latest_failed and latest_failed.error_message
            else "One or more analysis jobs failed."
        )
        return

    submission.status = "completed"
    submission.error_message = None


def _build_summary(raw_result: dict[str, Any]) -> str:
    final_grading = raw_result.get("final_grading")
    final_reasoning = (
        final_grading.get("overall_reasoning")
        if isinstance(final_grading, dict)
        else None
    )
    if isinstance(final_reasoning, str) and final_reasoning.strip():
        return final_reasoning

    ppt_summary = raw_result.get("ppt", {}).get("ppt_summary")
    repository_analysis = raw_result.get("repository", {}).get("repository_analysis", {})
    repo_summary = repository_analysis.get("executive_summary") if isinstance(repository_analysis, dict) else None
    video_parsed = raw_result.get("video", {}).get("parsed")
    video_summary = video_parsed.get("summary") if isinstance(video_parsed, dict) else None
    parts = [part for part in [ppt_summary, repo_summary, video_summary] if part]
    if parts:
        return "\n\n".join(parts)
    return "Analysis completed. See raw_result for details."


def _latest_component_results_for_submission(
    session: Session,
    submission_id: str,
) -> dict[str, dict[str, Any]]:
    component_map = {
        "git_analysis": "repository",
        "ppt_analysis": "ppt",
        "video_analysis": "video",
    }
    latest_jobs = _latest_jobs_by_type(session, submission_id, set(component_map.keys()))
    results: dict[str, dict[str, Any]] = {}
    for job_type, component_key in component_map.items():
        job = latest_jobs.get(job_type)
        if job is None:
            results[component_key] = {"missing": True}
            continue
        if job.status == "completed":
            normalized = _normalize_component_payload(job.result_json, component_key)
            results[component_key] = normalized or {"missing": True}
            continue
        if job.status == "failed":
            results[component_key] = {"error": job.error_message or "Analysis failed."}
            continue
        results[component_key] = {"pending": True}
    return results


def _normalize_component_payload(
    result_json: dict[str, Any] | None,
    component_key: str,
) -> dict[str, Any] | None:
    if not isinstance(result_json, dict):
        return None
    if isinstance(result_json.get(component_key), dict):
        return result_json[component_key]
    known_component_keys = {"repository", "ppt", "video", "final_grading"}
    if known_component_keys.intersection(result_json.keys()):
        return None
    return result_json


def _latest_jobs_by_type(
    session: Session,
    submission_id: str,
    job_types: set[str],
) -> dict[str, AnalysisJob]:
    jobs = list(
        session.scalars(
            select(AnalysisJob)
            .where(AnalysisJob.submission_id == submission_id)
            .order_by(AnalysisJob.updated_at.desc())
        )
    )
    latest: dict[str, AnalysisJob] = {}
    for job in jobs:
        job_type = (job.job_type or "").strip()
        if job_type not in job_types or job_type in latest:
            continue
        latest[job_type] = job
    return latest


def _maybe_enqueue_final_grading_job(
    session: Session,
    submission_id: str,
    settings: Settings,
    *,
    triggering_job_type: str | None = None,
) -> None:
    if triggering_job_type == "final_grading_analysis":
        return
    component_types = {"git_analysis", "ppt_analysis", "video_analysis"}
    latest_components = _latest_jobs_by_type(session, submission_id, component_types)
    if set(latest_components.keys()) != component_types:
        return
    if any(job.status in {"queued", "running"} for job in latest_components.values()):
        return
    if any(job.status != "completed" for job in latest_components.values()):
        return

    component_latest_ts = max(
        (job.updated_at or job.created_at)
        for job in latest_components.values()
    )
    final_jobs = list(
        session.scalars(
            select(AnalysisJob)
            .where(
                AnalysisJob.submission_id == submission_id,
                AnalysisJob.job_type == "final_grading_analysis",
            )
            .order_by(AnalysisJob.created_at.desc())
        )
    )
    if any(job.status in {"queued", "running"} for job in final_jobs):
        return

    latest_completed_final = next((job for job in final_jobs if job.status == "completed"), None)
    if latest_completed_final is not None:
        final_ts = latest_completed_final.completed_at or latest_completed_final.updated_at
        if final_ts is not None and final_ts >= component_latest_ts:
            return

    submission = session.get(Submission, submission_id)
    if submission is None:
        return
    payload = {
        "job_type": "final_grading_analysis",
        "submission_id": submission.id,
        "event_id": submission.event_id,
        "team_name": submission.team_name,
        "repo_url": submission.repo_url,
        "branch": submission.branch,
    }
    final_job = AnalysisJob(
        submission_id=submission.id,
        job_type="final_grading_analysis",
        status="queued",
        job_payload=payload,
    )
    session.add(final_job)
    session.flush()
    payload_with_id = {**payload, "job_id": final_job.id}
    final_job.job_payload = payload_with_id

    if settings.has_sqs_queue_configured():
        try:
            queue = SqsQueueService(settings)
            final_job.sqs_message_id = queue.send_analysis_job(payload_with_id)
        except Exception as exc:
            logger.exception("Unable to enqueue final grading job %s", final_job.id)
            final_job.status = "failed"
            final_job.error_message = f"Unable to enqueue final grading job: {exc}"


def _raise_if_no_successful_analysis(raw_result: dict[str, Any]) -> None:
    components = {
        name: value
        for name in ("repository", "ppt", "video")
        if isinstance((value := raw_result.get(name)), dict)
    }
    if not components:
        return

    errors = [
        f"{name}: {component['error']}"
        for name, component in components.items()
        if component.get("error")
    ]
    if not errors:
        return

    if any(_component_succeeded(component) for component in components.values()):
        return

    raise RuntimeError("; ".join(errors))


def _component_succeeded(component: dict[str, Any]) -> bool:
    if component.get("error") or component.get("skipped"):
        return False
    return any(
        component.get(key)
        for key in (
            "repository_analysis",
            "ppt_summary",
            "criteria_scores",
            "parsed",
            "raw_output",
        )
    )


def _first_artifact(
    artifacts: list[SubmissionArtifact],
    kinds: set[str],
) -> SubmissionArtifact | None:
    for artifact in artifacts:
        if artifact.kind in kinds:
            return artifact
    # Only apply filename-based fallbacks for PPT/PDF selection.
    # Video analysis must never "accidentally" pick a presentation file.
    if "ppt" in kinds:
        for artifact in artifacts:
            lower_path = PurePosixPath(artifact.object_key).name.lower()
            if lower_path.endswith((".pptx", ".pdf")):
                return artifact
    return None
