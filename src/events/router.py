from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.db.session import get_db_session
from src.events.schemas import EventCreateRequest, EventResponse
from src.events.service import (
    build_event_response,
    create_event,
    delete_event,
    get_event,
    list_events,
)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
def list_evaluation_events(session: Session = Depends(get_db_session)) -> list[EventResponse]:
    return list_events(session)


@router.post("", response_model=EventResponse)
def create_evaluation_event(
    request: EventCreateRequest,
    session: Session = Depends(get_db_session),
) -> EventResponse:
    event = create_event(session, request)
    return build_event_response(session, event)


@router.get("/{event_id}", response_model=EventResponse)
def get_evaluation_event(
    event_id: str,
    session: Session = Depends(get_db_session),
) -> EventResponse:
    event = get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return build_event_response(session, event)


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