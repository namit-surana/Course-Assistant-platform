from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.aws.s3_service import S3StorageService, build_upload_object_key
from src.aws.sqs_service import SqsQueueService
from src.config.settings import Settings, get_settings
from src.db.models import AnalysisJob, EvaluationEvent, FeedbackReport, Submission, SubmissionArtifact
from src.db.session import get_db_session
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
def start_submission_video_analysis(
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
    video_artifact = _pick_video_artifact(submission.artifacts)
    if video_artifact is None:
        raise HTTPException(status_code=400, detail="No video artifact found for this submission.")

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


@router.post(
    "/{submission_id}/git-analysis/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
def start_submission_git_analysis(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    if not submission.repo_url:
        raise HTTPException(status_code=400, detail="No repository URL found for this submission.")

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


@router.post(
    "/{submission_id}/ppt-analysis/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
def start_submission_ppt_analysis(
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

    ppt_artifact = _pick_ppt_artifact(submission.artifacts)
    if ppt_artifact is None:
        raise HTTPException(status_code=400, detail="No PPT/PDF artifact found for this submission.")

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


@router.post(
    "/{submission_id}/final-grading/start",
    response_model=SubmissionArtifactAnalysisStartResponse,
)
def start_submission_final_grading(
    submission_id: str,
    session: Session = Depends(get_db_session),
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
) -> SubmissionArtifactAnalysisStartResponse:
    submission = session.get(
        Submission,
        submission_id,
        options=[selectinload(Submission.analysis_jobs)],
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
