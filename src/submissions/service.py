from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.orm import Session, selectinload

from src.config.settings import Settings
from src.db.models import AnalysisJob, Submission, SubmissionArtifact
from src.submissions.schemas import SubmissionCreateRequest


class QueuePublisher(Protocol):
    def send_analysis_job(self, payload: dict[str, Any]) -> str | None: ...


@dataclass(frozen=True)
class CreatedSubmission:
    submission: Submission
    analysis_job: AnalysisJob
    queued: bool


def create_submission(
    session: Session,
    request: SubmissionCreateRequest,
    *,
    settings: Settings,
    queue_publisher: QueuePublisher | None = None,
) -> CreatedSubmission:
    rubric_snapshot = [criterion.model_dump(mode="json") for criterion in request.rubric_criteria]
    submission = Submission(
        event_id=request.event_id,
        assignment_id=request.assignment_id,
        team_name=request.team_name.strip(),
        submitter_email=request.submitter_email,
        repo_url=request.repo_url,
        branch=request.branch,
        status="queued",
        rubric_snapshot=rubric_snapshot or None,
    )
    session.add(submission)
    session.flush()

    for artifact_input in request.artifacts:
        session.add(
            SubmissionArtifact(
                submission_id=submission.id,
                kind=artifact_input.kind,
                bucket=settings.s3_bucket_name or "",
                object_key=artifact_input.object_key,
                file_name=artifact_input.file_name,
                content_type=artifact_input.content_type,
                size_bytes=artifact_input.size_bytes,
            )
        )

    job_payload = {
        "submission_id": submission.id,
        "event_id": submission.event_id,
        "team_name": submission.team_name,
        "repo_url": submission.repo_url,
        "branch": submission.branch,
    }
    analysis_job = AnalysisJob(
        submission_id=submission.id,
        status="queued",
        job_payload=job_payload,
    )
    session.add(analysis_job)
    session.flush()
    analysis_job.job_payload = {**job_payload, "job_id": analysis_job.id}
    session.commit()

    queued = False
    if queue_publisher is not None:
        try:
            analysis_job.sqs_message_id = queue_publisher.send_analysis_job(analysis_job.job_payload or {})
            queued = True
            session.commit()
        except Exception as exc:
            session.rollback()
            _mark_submission_failed(session, submission.id, analysis_job.id, str(exc))
            raise

    session.refresh(submission)
    session.refresh(analysis_job)
    return CreatedSubmission(
        submission=submission,
        analysis_job=analysis_job,
        queued=queued,
    )


def get_submission_detail(session: Session, submission_id: str) -> Submission | None:
    return session.get(
        Submission,
        submission_id,
        options=[
            selectinload(Submission.artifacts),
            selectinload(Submission.feedback_report),
        ],
    )


def _mark_submission_failed(
    session: Session,
    submission_id: str,
    analysis_job_id: str,
    error_message: str,
) -> None:
    submission = session.get(Submission, submission_id)
    analysis_job = session.get(AnalysisJob, analysis_job_id)
    if submission is not None:
        submission.status = "failed"
        submission.error_message = error_message
    if analysis_job is not None:
        analysis_job.status = "failed"
        analysis_job.error_message = error_message
    session.commit()
