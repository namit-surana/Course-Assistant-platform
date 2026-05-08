from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.api_ui.dependencies import get_analysis_run_service, get_run_store
from src.api_ui.models.schemas import (
    AnalysisRunState,
    build_final_grading_run_phases,
    build_ppt_run_phases,
    build_video_run_phases,
)
from src.api_ui.services.analysis_run_service import AnalysisRunService
from src.api_ui.services.crewai_live_events import bind_crewai_run_context
from src.api_ui.services.run_store import RunProgressReporter
from src.aws.s3_service import S3StorageService, build_upload_object_key
from src.aws.sqs_service import SqsQueueService
from src.config.settings import Settings, get_settings
from src.db.models import AnalysisJob, EvaluationEvent, FeedbackReport, FeedbackScore, Submission, SubmissionArtifact
from src.db.session import get_db_session, get_session_factory
from src.github_agent.phase1.models.schemas import AnalyzeRequest
from src.github_agent.phase1.services.context_builder import ContextBuilder
from src.github_agent.phase1.services.filter_service import FilterService
from src.github_agent.phase1.services.github_service import GitHubService
from src.github_agent.phase2.services.tree_analysis_service import create_tree_analysis_service
from src.github_agent.phase3.services.repository_analysis_service import create_repository_analysis_service
from src.ppt_agent.core import builtin_ppt_rubric_by_category
from src.ppt_agent.ppt_analyzer import analyze_ppt
from src.video_agent.services.analysis_runner import run_demo_video_analysis
from src.worker.processor import (
    _refresh_submission_status,
    _run_final_grading_analysis,
    _save_feedback,
)
from src.submissions.schemas import (
    FeedbackReportResponse,
    FeedbackScoreResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    SubmissionCreateRequest,
    SubmissionDetailResponse,
    SubmissionResponse,
    SubmissionArtifactAnalysisStartResponse,
    SubmissionArtifactResponse,
)
from src.submissions.service import create_submission, create_submission_analysis_job


router = APIRouter(prefix="/submissions", tags=["submissions"])


def get_queue_publisher(settings: Settings = Depends(get_settings)) -> SqsQueueService | None:
    if not settings.has_sqs_queue_configured():
        return None
    return SqsQueueService(settings)


@router.post("/presigned-url", response_model=PresignedUploadResponse)
def create_presigned_upload(
    request: PresignedUploadRequest,
    settings: Settings = Depends(get_settings),
) -> PresignedUploadResponse:
    try:
        storage = S3StorageService(settings)
        object_key = build_upload_object_key(
            kind=request.kind,
            file_name=request.file_name,
            submission_id=request.submission_id,
        )
        return PresignedUploadResponse(
            **storage.create_presigned_put_url(
                object_key=object_key,
                content_type=request.content_type,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=SubmissionResponse)
def submit_project(
    request: SubmissionCreateRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SubmissionResponse:
    try:
        created = create_submission(
            session,
            request,
            settings=settings,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SubmissionResponse(
        id=created.submission.id,
        status=created.submission.status,
        queued=False,
    )


@router.post(
    "/{submission_id}/processing/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
def start_submission_processing(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[selectinload(Submission.artifacts)],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        created = create_submission_analysis_job(
            session,
            submission,
            job_type="submission_analysis",
            queue_publisher=queue_publisher,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SubmissionArtifactAnalysisStartResponse(
        submission_id=submission.id,
        job_id=created.analysis_job.id,
        job_type=created.analysis_job.job_type,
        status=created.analysis_job.status,
        queued=created.queued,
        sqs_message_id=created.analysis_job.sqs_message_id,
    )


@router.post(
    "/{submission_id}/video-analysis/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
async def start_submission_video_analysis(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
    settings: Settings = Depends(get_settings),
    run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[selectinload(Submission.artifacts)],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    video_artifact = _pick_video_artifact(submission.artifacts)
    if video_artifact is None:
        raise HTTPException(status_code=400, detail="No video artifact found for this submission.")

    if not settings.video_analysis_inprocess:
        try:
            created = create_submission_analysis_job(
                session,
                submission,
                job_type="video_analysis",
                queue_publisher=queue_publisher,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return SubmissionArtifactAnalysisStartResponse(
            submission_id=submission.id,
            job_id=created.analysis_job.id,
            job_type=created.analysis_job.job_type,
            status=created.analysis_job.status,
            queued=created.queued,
            sqs_message_id=created.analysis_job.sqs_message_id,
        )

    job = AnalysisJob(
        submission_id=submission.id,
        job_type="video_analysis",
        status="running",
    )
    submission.status = "running"
    submission.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)

    artifact_object_key = video_artifact.object_key
    artifact_file_name = video_artifact.file_name
    job_id = job.id
    submission_id_value = submission.id
    label = artifact_file_name or "demo video"

    async def runner(reporter: RunProgressReporter) -> dict:
        return await _run_video_in_process(
            reporter,
            settings,
            artifact_object_key=artifact_object_key,
            artifact_file_name=artifact_file_name,
        )

    async def on_finish(final_state: AnalysisRunState) -> None:
        await _persist_inprocess_video_run(submission_id_value, job_id, final_state)

    run_state = await run_service.start_simple_run(
        kind="video",
        phases=build_video_run_phases(),
        runner=runner,
        label=label,
        on_finish=on_finish,
    )

    return SubmissionArtifactAnalysisStartResponse(
        submission_id=submission.id,
        job_id=job.id,
        job_type="video_analysis",
        status="running",
        queued=False,
        sqs_message_id=None,
        run_id=run_state.id,
    )


async def _run_video_in_process(
    reporter: RunProgressReporter,
    settings: Settings,
    *,
    artifact_object_key: str,
    artifact_file_name: str | None,
) -> dict:
    import asyncio
    import tempfile
    from pathlib import Path

    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not configured.")

    suffix = Path(artifact_file_name or artifact_object_key).suffix or ".mp4"

    reporter.start_subtask("video", "download", "Downloading video from S3")
    storage = S3StorageService(settings)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()

    loop = asyncio.get_running_loop()

    def _mark_uploaded() -> None:
        try:
            loop.call_soon_threadsafe(
                lambda: reporter.complete_subtask(
                    "video", "upload_to_gemini", "Video uploaded to Gemini"
                )
            )
            loop.call_soon_threadsafe(
                lambda: reporter.start_subtask(
                    "video", "wait_active", "Waiting for Gemini to activate the video"
                )
            )
        except Exception:  # noqa: BLE001
            pass

    def _mark_active() -> None:
        try:
            loop.call_soon_threadsafe(
                lambda: reporter.complete_subtask(
                    "video", "wait_active", "Gemini activated the video"
                )
            )
        except Exception:  # noqa: BLE001
            pass

    def _mark_score_started() -> None:
        try:
            loop.call_soon_threadsafe(
                lambda: reporter.start_subtask(
                    "video", "score", "Gemini is watching the video and scoring"
                )
            )
        except Exception:  # noqa: BLE001
            pass

    try:
        await asyncio.to_thread(storage.download_file, artifact_object_key, tmp.name)
        reporter.complete_subtask(
            "video",
            "download",
            f"Downloaded {artifact_file_name or artifact_object_key}",
        )

        reporter.start_subtask("video", "upload_to_gemini", "Uploading video to Gemini Files API")
        # Score subtask transitions are driven by the on_uploaded/on_active/on_score_started
        # callbacks fired by gemini_video.analyze_video_file.
        with bind_crewai_run_context(
            reporter,
            phase_id="video",
            default_subtask_id="score",
        ):
            raw, parsed = await asyncio.to_thread(
                run_demo_video_analysis,
                Path(tmp.name),
                "Course project demo",
                [],
                settings,
                _mark_uploaded,
                _mark_active,
                _mark_score_started,
            )
        reporter.complete_subtask("video", "score", "Scoring completed")
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    reporter.start_subtask("video", "save", "Saving feedback to the submission")
    return {"video": {"raw_output": raw, "parsed": parsed}}


async def _persist_inprocess_video_run(
    submission_id: str,
    job_id: str,
    final_state: AnalysisRunState,
) -> None:
    import asyncio
    from datetime import datetime, timezone

    def _write() -> None:
        session_factory = get_session_factory()
        with session_factory() as session:
            job = session.get(AnalysisJob, job_id)
            submission = session.get(
                Submission,
                submission_id,
                options=[selectinload(Submission.feedback_report)],
            )
            if job is None or submission is None:
                return

            now = datetime.now(timezone.utc)
            reporter = RunProgressReporter(get_run_store(), final_state.id)

            if final_state.status == "completed" and final_state.result_simple is not None:
                video_payload = (
                    final_state.result_simple.get("video", {})
                    if isinstance(final_state.result_simple, dict)
                    else {}
                )
                raw_result = {"video": video_payload}

                report = submission.feedback_report
                if report is None:
                    report = FeedbackReport(submission_id=submission.id, raw_result={})
                    session.add(report)
                    session.flush()
                merged = dict(report.raw_result or {})
                merged.update(raw_result)
                report.raw_result = merged
                summary = ((video_payload or {}).get("parsed") or {}).get("summary")
                if summary:
                    report.summary = summary
                session.add(report)

                job.status = "completed"
                job.result_json = raw_result
                job.completed_at = now
                job.error_message = None
                if submission.status != "failed":
                    submission.status = "completed"
                    submission.error_message = None
                reporter.complete_subtask("video", "save", "Feedback saved to the submission")
            else:
                error_message = final_state.error or "Video analysis failed."
                job.status = "failed"
                job.error_message = error_message
                job.result_json = {"error": error_message}
                job.completed_at = now
                submission.status = "failed"
                submission.error_message = error_message

            session.commit()

    await asyncio.to_thread(_write)


@router.post(
    "/{submission_id}/git-analysis/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
async def start_submission_git_analysis(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
    settings: Settings = Depends(get_settings),
    run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not submission.repo_url:
        raise HTTPException(status_code=400, detail="No repository URL found for this submission.")

    if not settings.git_analysis_inprocess:
        created = create_submission_analysis_job(
            session,
            submission,
            job_type="git_analysis",
            queue_publisher=queue_publisher,
        )
        return SubmissionArtifactAnalysisStartResponse(
            submission_id=submission.id,
            job_id=created.analysis_job.id,
            job_type=created.analysis_job.job_type,
            status=created.analysis_job.status,
            queued=created.queued,
            sqs_message_id=created.analysis_job.sqs_message_id,
        )

    # In-process path: run Phase 1/2/3 inside the API and stream live progress
    # via the AnalysisRunStore, so the frontend can poll /runs/{run_id}.
    job = AnalysisJob(
        submission_id=submission.id,
        job_type="git_analysis",
        status="running",
    )
    submission.status = "running"
    submission.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)

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

    job_id = job.id
    submission_id_value = submission.id

    async def on_finish(final_state: AnalysisRunState) -> None:
        await _persist_inprocess_git_run(submission_id_value, job_id, final_state)

    run_state = await run_service.start_run(
        AnalyzeRequest(repo_url=submission.repo_url, branch=submission.branch),
        github_service=github_service,
        filter_service=filter_service,
        context_builder=context_builder,
        tree_analysis_service=tree_analysis_service,
        repository_analysis_service=repository_analysis_service,
        on_finish=on_finish,
    )

    return SubmissionArtifactAnalysisStartResponse(
        submission_id=submission.id,
        job_id=job.id,
        job_type="git_analysis",
        status="running",
        queued=False,
        sqs_message_id=None,
        run_id=run_state.id,
    )


async def _persist_inprocess_git_run(
    submission_id: str,
    job_id: str,
    final_state: AnalysisRunState,
) -> None:
    """Mirror the worker's _save_feedback for in-process git runs."""

    import asyncio
    from datetime import datetime, timezone

    def _write() -> None:
        session_factory = get_session_factory()
        with session_factory() as session:
            job = session.get(AnalysisJob, job_id)
            submission = session.get(Submission, submission_id)
            if job is None or submission is None:
                return

            now = datetime.now(timezone.utc)
            if final_state.status == "completed" and final_state.result is not None:
                repository_payload = final_state.result.model_dump(mode="json")
                raw_result = {"repository": repository_payload}
                report = submission.feedback_report
                if report is None:
                    report = FeedbackReport(submission_id=submission.id, raw_result={})
                    session.add(report)
                    session.flush()
                merged = dict(report.raw_result or {})
                merged.update(raw_result)
                report.raw_result = merged
                exec_summary = (
                    repository_payload.get("repository_analysis", {}).get("executive_summary")
                    if isinstance(repository_payload.get("repository_analysis"), dict)
                    else None
                )
                report.summary = exec_summary or report.summary
                session.add(report)

                job.status = "completed"
                job.result_json = raw_result
                job.completed_at = now
                job.error_message = None
                submission.status = "completed"
                submission.error_message = None
            else:
                error_message = final_state.error or "Repository analysis failed."
                job.status = "failed"
                job.error_message = error_message
                job.result_json = {"error": error_message}
                job.completed_at = now
                submission.status = "failed"
                submission.error_message = error_message

            session.commit()

    await asyncio.to_thread(_write)


@router.post(
    "/{submission_id}/ppt-analysis/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
async def start_submission_ppt_analysis(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
    settings: Settings = Depends(get_settings),
    run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[selectinload(Submission.artifacts)],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    ppt_artifact = _pick_ppt_artifact(submission.artifacts)
    if ppt_artifact is None:
        raise HTTPException(status_code=400, detail="No PPT/PDF artifact found for this submission.")

    if not settings.ppt_analysis_inprocess:
        created = create_submission_analysis_job(
            session,
            submission,
            job_type="ppt_analysis",
            queue_publisher=queue_publisher,
        )
        return SubmissionArtifactAnalysisStartResponse(
            submission_id=submission.id,
            job_id=created.analysis_job.id,
            job_type=created.analysis_job.job_type,
            status=created.analysis_job.status,
            queued=created.queued,
            sqs_message_id=created.analysis_job.sqs_message_id,
        )

    job = AnalysisJob(
        submission_id=submission.id,
        job_type="ppt_analysis",
        status="running",
    )
    submission.status = "running"
    submission.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)

    artifact_object_key = ppt_artifact.object_key
    artifact_file_name = ppt_artifact.file_name
    job_id = job.id
    submission_id_value = submission.id
    label = artifact_file_name or "presentation"

    async def runner(reporter: RunProgressReporter) -> dict:
        return await _run_ppt_in_process(
            reporter,
            settings,
            artifact_object_key=artifact_object_key,
            artifact_file_name=artifact_file_name,
        )

    async def on_finish(final_state: AnalysisRunState) -> None:
        await _persist_inprocess_ppt_run(submission_id_value, job_id, final_state)

    run_state = await run_service.start_simple_run(
        kind="ppt",
        phases=build_ppt_run_phases(),
        runner=runner,
        label=label,
        on_finish=on_finish,
    )

    return SubmissionArtifactAnalysisStartResponse(
        submission_id=submission.id,
        job_id=job.id,
        job_type="ppt_analysis",
        status="running",
        queued=False,
        sqs_message_id=None,
        run_id=run_state.id,
    )


async def _run_ppt_in_process(
    reporter: RunProgressReporter,
    settings: Settings,
    *,
    artifact_object_key: str,
    artifact_file_name: str | None,
) -> dict:
    import asyncio
    import tempfile
    from pathlib import Path

    suffix = Path(artifact_file_name or artifact_object_key).suffix
    if suffix.lower() not in {".pptx", ".pdf"}:
        suffix = ".pptx"

    reporter.start_subtask("ppt", "download", "Downloading PPT/PDF from S3")
    storage = S3StorageService(settings)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    try:
        await asyncio.to_thread(storage.download_file, artifact_object_key, tmp.name)
        reporter.complete_subtask(
            "ppt",
            "download",
            f"Downloaded {artifact_file_name or artifact_object_key}",
        )

        reporter.start_subtask(
            "ppt",
            "extract",
            "Slide text will be read on-demand by the rubric agent",
        )
        reporter.complete_subtask("ppt", "extract", "Extraction will run via the agent tool")

        reporter.start_subtask("ppt", "score", "Scoring against rubric with Gemini")
        with bind_crewai_run_context(
            reporter,
            phase_id="ppt",
            default_subtask_id="score",
        ):
            result = await asyncio.to_thread(analyze_ppt, tmp.name)
        reporter.complete_subtask("ppt", "score", "Scoring completed")
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    reporter.start_subtask("ppt", "save", "Saving feedback to the submission")
    return {"ppt": result}


async def _persist_inprocess_ppt_run(
    submission_id: str,
    job_id: str,
    final_state: AnalysisRunState,
) -> None:
    import asyncio
    from datetime import datetime, timezone

    def _write() -> None:
        session_factory = get_session_factory()
        with session_factory() as session:
            job = session.get(AnalysisJob, job_id)
            submission = session.get(
                Submission,
                submission_id,
                options=[selectinload(Submission.feedback_report)],
            )
            if job is None or submission is None:
                return

            now = datetime.now(timezone.utc)
            reporter = RunProgressReporter(get_run_store(), final_state.id)

            if final_state.status == "completed" and final_state.result_simple is not None:
                ppt_payload = final_state.result_simple.get("ppt", {}) if isinstance(
                    final_state.result_simple, dict
                ) else {}
                raw_result = {"ppt": ppt_payload}

                report = submission.feedback_report
                if report is None:
                    report = FeedbackReport(submission_id=submission.id, raw_result={})
                    session.add(report)
                    session.flush()
                merged = dict(report.raw_result or {})
                merged.update(raw_result)
                report.raw_result = merged
                summary = (ppt_payload or {}).get("ppt_summary")
                if summary:
                    report.summary = summary
                session.add(report)

                rubric_by_category = builtin_ppt_rubric_by_category()
                ppt_categories = set(rubric_by_category.keys())
                for existing_score in list(report.scores):
                    if existing_score.category in ppt_categories:
                        session.delete(existing_score)
                session.flush()

                for score_item in (ppt_payload or {}).get("criteria_scores", []):
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

                job.status = "completed"
                job.result_json = raw_result
                job.completed_at = now
                job.error_message = None
                if submission.status != "failed":
                    submission.status = "completed"
                    submission.error_message = None
                reporter.complete_subtask("ppt", "save", "Feedback saved to the submission")
            else:
                error_message = final_state.error or "PPT analysis failed."
                job.status = "failed"
                job.error_message = error_message
                job.result_json = {"error": error_message}
                job.completed_at = now
                submission.status = "failed"
                submission.error_message = error_message

            session.commit()

    await asyncio.to_thread(_write)


async def _persist_inprocess_final_grading_run(
    submission_id: str,
    job_id: str,
    *,
    live_run_id: str,
    final_state: AnalysisRunState,
) -> None:
    from datetime import datetime, timezone

    def _write() -> None:
        session_factory = get_session_factory()
        with session_factory() as session:
            job = session.get(AnalysisJob, job_id)
            submission = session.get(
                Submission,
                submission_id,
                options=[selectinload(Submission.feedback_report)],
            )
            if job is None or submission is None:
                return

            now = datetime.now(timezone.utc)
            reporter = RunProgressReporter(get_run_store(), live_run_id)

            if final_state.status == "completed" and final_state.result_simple is not None:
                rs = final_state.result_simple
                fg = rs.get("final_grading") if isinstance(rs, dict) else None
                if not isinstance(fg, dict):
                    error_message = "Final grading did not return structured output."
                    job.status = "failed"
                    job.error_message = error_message
                    job.result_json = {"error": error_message}
                    job.completed_at = now
                    submission.status = "failed"
                    submission.error_message = error_message
                else:
                    raw_result = {"final_grading": fg}
                    _save_feedback(session, submission, raw_result)
                    job.status = "completed"
                    job.result_json = raw_result
                    job.completed_at = now
                    job.error_message = None
                    if submission.status != "failed":
                        submission.status = "completed"
                        submission.error_message = None
                    reporter.complete_subtask(
                        "final",
                        "save",
                        "Final report saved to database",
                    )
            else:
                error_message = final_state.error or "Final grading failed."
                job.status = "failed"
                job.error_message = error_message
                job.result_json = {"error": error_message}
                job.completed_at = now
                submission.status = "failed"
                submission.error_message = error_message

            _refresh_submission_status(session, submission_id)
            session.commit()

    await asyncio.to_thread(_write)


@router.post(
    "/{submission_id}/final-grading/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
async def start_submission_final_grading(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
    settings: Settings = Depends(get_settings),
    run_service: AnalysisRunService = Depends(get_analysis_run_service),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[selectinload(Submission.analysis_jobs), selectinload(Submission.artifacts)],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    event = session.get(EvaluationEvent, submission.event_id) if submission.event_id else None
    if not event or not event.criteria_config:
        raise HTTPException(status_code=400, detail="Event criteria_config is required for final grading.")

    component_job_types = {"git_analysis", "ppt_analysis", "video_analysis"}
    has_component_job = any(
        (job.job_type or "").strip() in component_job_types
        for job in submission.analysis_jobs
    )
    if not has_component_job:
        raise HTTPException(status_code=400, detail="Run at least one component analysis before final grading.")

    has_active_final_job = any(
        (job.job_type or "").strip() == "final_grading_analysis" and job.status in {"queued", "running"}
        for job in submission.analysis_jobs
    )
    if has_active_final_job:
        raise HTTPException(status_code=409, detail="A final grading job is already queued or running.")

    if not settings.final_grading_inprocess:
        created = create_submission_analysis_job(
            session,
            submission,
            job_type="final_grading_analysis",
            queue_publisher=queue_publisher,
        )
        return SubmissionArtifactAnalysisStartResponse(
            submission_id=submission.id,
            job_id=created.analysis_job.id,
            job_type=created.analysis_job.job_type,
            status=created.analysis_job.status,
            queued=created.queued,
            sqs_message_id=created.analysis_job.sqs_message_id,
        )

    job = AnalysisJob(
        submission_id=submission.id,
        job_type="final_grading_analysis",
        status="running",
    )
    submission.status = "running"
    submission.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)

    job_id = job.id
    submission_id_value = submission.id
    loop = asyncio.get_running_loop()

    async def runner(reporter: RunProgressReporter) -> dict[str, Any]:
        reporter.start_subtask(
            "final",
            "load_context",
            "Loading rubric criteria and component analysis outputs…",
        )

        def on_context_ready() -> None:
            def _bump() -> None:
                reporter.complete_subtask(
                    "final",
                    "load_context",
                    "Loaded criteria and latest component results",
                )
                reporter.start_subtask(
                    "final",
                    "crew_review",
                    "Synthesizing final scores with CrewAI",
                )

            loop.call_soon_threadsafe(_bump)

        def work() -> dict[str, Any]:
            cm = bind_crewai_run_context(
                reporter,
                phase_id="final",
                default_subtask_id="crew_review",
                task_name_map={"final_grading": "crew_review"},
            )
            session_factory = get_session_factory()
            with session_factory() as db_session:
                sub = db_session.get(
                    Submission,
                    submission_id_value,
                    options=[
                        selectinload(Submission.artifacts),
                        selectinload(Submission.analysis_jobs),
                    ],
                )
                if sub is None:
                    raise RuntimeError("Submission not found.")
                return _run_final_grading_analysis(
                    db_session,
                    sub,
                    settings,
                    crew_context=cm,
                    on_context_ready=on_context_ready,
                )

        payload = await asyncio.to_thread(work)
        reporter.complete_subtask(
            "final",
            "crew_review",
            "Final criterion scores generated",
        )
        reporter.start_subtask(
            "final",
            "save",
            "Saving final grades to the submission…",
        )
        return {"final_grading": payload}

    async def on_finish(final_state: AnalysisRunState) -> None:
        await _persist_inprocess_final_grading_run(
            submission_id_value,
            job_id,
            live_run_id=final_state.id,
            final_state=final_state,
        )

    run_state = await run_service.start_simple_run(
        kind="final",
        phases=build_final_grading_run_phases(),
        runner=runner,
        label="final grading",
        on_finish=on_finish,
    )

    return SubmissionArtifactAnalysisStartResponse(
        submission_id=submission.id,
        job_id=job.id,
        job_type="final_grading_analysis",
        status="running",
        queued=False,
        sqs_message_id=None,
        run_id=run_state.id,
    )


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
def get_submission(
    submission_id: str,
    session: Session = Depends(get_db_session),
) -> SubmissionDetailResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[
            selectinload(Submission.artifacts),
            selectinload(Submission.feedback_report).selectinload(FeedbackReport.scores),
            selectinload(Submission.analysis_jobs),
        ],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    feedback = _build_feedback_response(submission)

    return SubmissionDetailResponse(
        id=submission.id,
        event_id=submission.event_id,
        team_name=submission.team_name,
        repo_url=submission.repo_url,
        branch=submission.branch,
        status=submission.status,
        error_message=submission.error_message,
        artifacts=[
            SubmissionArtifactResponse(
                id=artifact.id,
                kind=artifact.kind,
                bucket=artifact.bucket,
                object_key=artifact.object_key,
                file_name=artifact.file_name,
                content_type=artifact.content_type,
                size_bytes=artifact.size_bytes,
                status=artifact.status,
            )
            for artifact in submission.artifacts
        ],
        feedback=feedback,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


@router.get("/events/{event_id}/items", response_model=list[SubmissionDetailResponse])
def list_event_submissions(
    event_id: str,
    session: Session = Depends(get_db_session),
) -> list[SubmissionDetailResponse]:
    statement = (
        select(Submission)
        .where(Submission.event_id == event_id)
        .options(
            selectinload(Submission.artifacts),
            selectinload(Submission.feedback_report).selectinload(FeedbackReport.scores),
            selectinload(Submission.analysis_jobs),
        )
        .order_by(Submission.created_at.desc())
    )
    return [_submission_to_detail(submission) for submission in session.scalars(statement)]


def _submission_to_detail(submission: Submission) -> SubmissionDetailResponse:
    feedback = _build_feedback_response(submission)

    return SubmissionDetailResponse(
        id=submission.id,
        event_id=submission.event_id,
        team_name=submission.team_name,
        repo_url=submission.repo_url,
        branch=submission.branch,
        status=submission.status,
        error_message=submission.error_message,
        artifacts=[
            SubmissionArtifactResponse(
                id=artifact.id,
                kind=artifact.kind,
                bucket=artifact.bucket,
                object_key=artifact.object_key,
                file_name=artifact.file_name,
                content_type=artifact.content_type,
                size_bytes=artifact.size_bytes,
                status=artifact.status,
            )
            for artifact in submission.artifacts
        ],
        feedback=feedback,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


def _build_feedback_response(submission: Submission) -> FeedbackReportResponse | None:
    report = submission.feedback_report
    fallback_scores = (
        [
            FeedbackScoreResponse(
                category=score.category,
                score=float(score.score),
                max_score=float(score.max_score) if score.max_score is not None else None,
                comment=score.comment,
            )
            for score in report.scores
        ]
        if report is not None
        else []
    )
    final_result = _latest_completed_final_result(submission.analysis_jobs)
    final_scores = _scores_from_final_result(final_result) if final_result is not None else []
    scores = final_scores or fallback_scores

    merged_raw_result = _merge_job_results(
        submission.analysis_jobs,
        fallback_raw_result=report.raw_result if report is not None else None,
    )
    if final_result is not None:
        merged_raw_result = dict(merged_raw_result or {})
        merged_raw_result["final_grading"] = final_result
    latest_final_job = _latest_job_by_type(submission.analysis_jobs, "final_grading_analysis")
    if latest_final_job is not None:
        merged_raw_result = dict(merged_raw_result or {})
        merged_raw_result["final_grading_status"] = {
            "status": latest_final_job.status,
            "error": latest_final_job.error_message,
        }

    summary = (
        final_result.get("overall_reasoning")
        if isinstance(final_result, dict)
        else None
    )
    if not isinstance(summary, str) or not summary.strip():
        summary = (
            _build_summary_from_raw_result(merged_raw_result)
            if merged_raw_result
            else (report.summary if report is not None else None)
        )

    if report is None and not merged_raw_result:
        return None

    return FeedbackReportResponse(
        summary=summary,
        raw_result=merged_raw_result,
        scores=scores,
    )


def _latest_completed_final_result(
    analysis_jobs: list[AnalysisJob],
) -> dict[str, object] | None:
    latest_job = _latest_job_by_type(analysis_jobs, "final_grading_analysis", status="completed")
    if latest_job is None or not isinstance(latest_job.result_json, dict):
        return None
    result_json = latest_job.result_json
    wrapped = result_json.get("final_grading")
    if isinstance(wrapped, dict):
        return wrapped
    return result_json


def _scores_from_final_result(final_result: dict[str, object]) -> list[FeedbackScoreResponse]:
    criterion_grades = final_result.get("criterion_grades")
    if not isinstance(criterion_grades, list):
        return []
    scores: list[FeedbackScoreResponse] = []
    for grade in criterion_grades:
        if not isinstance(grade, dict):
            continue
        criterion = grade.get("criterion")
        score = grade.get("score")
        if not isinstance(criterion, str):
            continue
        if not isinstance(score, (int, float)):
            continue
        max_score = grade.get("max_score")
        scores.append(
            FeedbackScoreResponse(
                category=criterion,
                score=float(score),
                max_score=float(max_score) if isinstance(max_score, (int, float)) else None,
                comment=grade.get("reasoning") if isinstance(grade.get("reasoning"), str) else None,
            )
        )
    return scores


def _latest_job_by_type(
    analysis_jobs: list[AnalysisJob],
    job_type: str,
    *,
    status: str | None = None,
) -> AnalysisJob | None:
    latest_job: AnalysisJob | None = None
    for job in analysis_jobs:
        if (job.job_type or "").strip() != job_type:
            continue
        if status is not None and job.status != status:
            continue
        if latest_job is None:
            latest_job = job
            continue
        latest_ts = latest_job.updated_at or latest_job.created_at
        candidate_ts = job.updated_at or job.created_at
        if candidate_ts >= latest_ts:
            latest_job = job
    return latest_job


def _merge_job_results(
    analysis_jobs: list[AnalysisJob],
    *,
    fallback_raw_result: dict[str, object] | None,
) -> dict[str, object] | None:
    merged: dict[str, object] = dict(fallback_raw_result or {})
    latest_by_type: dict[str, AnalysisJob] = {}

    for job in analysis_jobs:
        job_type = (job.job_type or "").strip()
        if not job_type:
            continue
        current = latest_by_type.get(job_type)
        if current is None:
            latest_by_type[job_type] = job
            continue
        current_ts = current.updated_at or current.created_at
        candidate_ts = job.updated_at or job.created_at
        if candidate_ts >= current_ts:
            latest_by_type[job_type] = job

    if "submission_analysis" in latest_by_type:
        submission_job = latest_by_type["submission_analysis"]
        if submission_job.status == "completed" and isinstance(submission_job.result_json, dict):
            for key in ("repository", "ppt", "video"):
                component = submission_job.result_json.get(key)
                if isinstance(component, dict):
                    merged[key] = component

    component_by_job_type = {
        "git_analysis": "repository",
        "ppt_analysis": "ppt",
        "video_analysis": "video",
    }
    for job_type, component_key in component_by_job_type.items():
        job = latest_by_type.get(job_type)
        if job is None:
            continue
        if job.status == "failed":
            merged[component_key] = {"error": job.error_message or "Analysis failed."}
            continue
        if job.status != "completed":
            continue
        normalized = _normalize_component_payload(job.result_json, component_key)
        if normalized is not None:
            merged[component_key] = normalized

    return merged or None


def _normalize_component_payload(
    result_json: dict[str, object] | None,
    component_key: str,
) -> dict[str, object] | None:
    if not isinstance(result_json, dict):
        return None
    if isinstance(result_json.get(component_key), dict):
        return result_json[component_key]  # type: ignore[return-value]

    known_component_keys = {"repository", "ppt", "video"}
    if known_component_keys.intersection(result_json.keys()):
        return None
    return result_json


def _build_summary_from_raw_result(raw_result: dict[str, object]) -> str:
    final_grading = raw_result.get("final_grading")
    final_summary = (
        final_grading.get("overall_reasoning")
        if isinstance(final_grading, dict)
        else None
    )
    if isinstance(final_summary, str) and final_summary.strip():
        return final_summary

    ppt = raw_result.get("ppt")
    ppt_summary = ppt.get("ppt_summary") if isinstance(ppt, dict) else None

    repository = raw_result.get("repository")
    repository_analysis = repository.get("repository_analysis") if isinstance(repository, dict) else None
    repo_summary = (
        repository_analysis.get("executive_summary")
        if isinstance(repository_analysis, dict)
        else None
    )

    video = raw_result.get("video")
    video_parsed = video.get("parsed") if isinstance(video, dict) else None
    video_summary = video_parsed.get("summary") if isinstance(video_parsed, dict) else None

    parts = [part for part in [ppt_summary, repo_summary, video_summary] if isinstance(part, str) and part.strip()]
    if parts:
        return "\n\n".join(parts)
    return "Analysis completed. See raw_result for details."


def _pick_video_artifact(artifacts: list[SubmissionArtifact]) -> SubmissionArtifact | None:
    candidates = [artifact for artifact in artifacts if artifact.kind == "video"]
    if not candidates:
        return None
    candidates.sort(key=lambda artifact: artifact.created_at, reverse=True)
    return candidates[0]


def _pick_ppt_artifact(artifacts: list[SubmissionArtifact]) -> SubmissionArtifact | None:
    candidates = [artifact for artifact in artifacts if artifact.kind == "ppt"]
    if not candidates:
        return None
    candidates.sort(key=lambda artifact: artifact.created_at, reverse=True)
    return candidates[0]
