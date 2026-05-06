from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from src.config.settings import Settings, get_settings
from src.db.models import FeedbackReport, Submission
from src.db.session import get_db_session
from src.events.schemas import EventCreateRequest, EventResponse
from src.events.service import (
    build_event_response,
    create_event,
    delete_event,
    get_event,
    list_events,
)
from src.submissions.schemas import (
    FeedbackReportResponse,
    FeedbackScoreResponse,
    SubmissionArtifactResponse,
    SubmissionDetailResponse,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
def list_evaluation_events(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[EventResponse]:
    return list_events(session, settings)


@router.post("", response_model=EventResponse)
def create_evaluation_event(
    request: EventCreateRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> EventResponse:
    event = create_event(session, request)
    return build_event_response(session, event, settings)


@router.get("/{event_id}", response_model=EventResponse)
def get_evaluation_event(
    event_id: str,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> EventResponse:
    event = get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return build_event_response(session, event, settings)


@router.delete("/{event_id}", status_code=204)
def delete_evaluation_event(
    event_id: str,
    session: Session = Depends(get_db_session),
) -> Response:
    event = get_event(session, event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    delete_event(session, event)

    return Response(status_code=204)


@router.get("/{event_id}/submissions", response_model=list[SubmissionDetailResponse])
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

    items: list[SubmissionDetailResponse] = []
    for submission in session.scalars(statement):
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

        items.append(
            SubmissionDetailResponse(
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
        )

    return items