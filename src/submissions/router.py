from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.aws.s3_service import S3StorageService, build_upload_object_key
from src.aws.sqs_service import SqsQueueService
from src.config.settings import Settings, get_settings
from src.db.models import FeedbackReport, Submission
from src.db.session import get_db_session
from src.submissions.schemas import (
    FeedbackReportResponse,
    FeedbackScoreResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    SubmissionCreateRequest,
    SubmissionDetailResponse,
    SubmissionResponse,
    SubmissionArtifactResponse,
)
from src.submissions.service import create_submission


router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def get_queue_publisher(settings: Settings = Depends(get_settings)) -> SqsQueueService | None:
    if not settings.sqs_queue_url:
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
    queue_publisher: SqsQueueService | None = Depends(get_queue_publisher),
) -> SubmissionResponse:
    try:
        created = create_submission(
            session,
            request,
            settings=settings,
            queue_publisher=queue_publisher,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SubmissionResponse(
        id=created.submission.id,
        status=created.submission.status,
        analysis_job_id=created.analysis_job.id,
        sqs_message_id=created.analysis_job.sqs_message_id,
        queued=created.queued,
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
        ],
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    feedback = None
    if submission.feedback_report is not None:
        feedback = FeedbackReportResponse(
            summary=submission.feedback_report.summary,
            raw_result=submission.feedback_report.raw_result,
            scores=[
                FeedbackScoreResponse(
                    category=score.category,
                    score=float(score.score),
                    max_score=float(score.max_score) if score.max_score is not None else None,
                    comment=score.comment,
                )
                for score in submission.feedback_report.scores
            ],
        )

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
        )
        .order_by(Submission.created_at.desc())
    )
    return [_submission_to_detail(submission) for submission in session.scalars(statement)]


def _submission_to_detail(submission: Submission) -> SubmissionDetailResponse:
    feedback = None
    if submission.feedback_report is not None:
        feedback = FeedbackReportResponse(
            summary=submission.feedback_report.summary,
            raw_result=submission.feedback_report.raw_result,
            scores=[
                FeedbackScoreResponse(
                    category=score.category,
                    score=float(score.score),
                    max_score=float(score.max_score) if score.max_score is not None else None,
                    comment=score.comment,
                )
                for score in submission.feedback_report.scores
            ],
        )

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
