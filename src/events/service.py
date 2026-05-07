from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.db.models import Assignment, EvaluationEvent, RubricCriterion, Submission
from src.events.schemas import EventCreateRequest, EventResponse


CRITERION_LABELS: dict[str, str] = {
    "repo_completeness": "Repository completeness",
    "repo_impl_quality": "Implementation quality",
    "repo_code_quality": "Code quality",
    "repo_documentation": "Repository documentation",
    "repo_depth": "Technical depth",
    "pres_clarity": "Presentation clarity",
    "pres_structure": "Presentation structure",
    "pres_solution": "Solution explanation",
    "pres_design": "Design and architecture",
    "pres_impact": "Impact and results",
    "report_problem": "Problem framing",
    "report_methodology": "Methodology",
    "report_depth": "Report depth",
    "report_results": "Results and evaluation",
    "report_writing": "Writing quality",
    "demo_clarity": "Demo clarity",
    "demo_coverage": "Demo coverage",
    "demo_functionality": "Demo functionality",
    "demo_narration": "Demo narration",
    "demo_quality": "Demo quality",
    "live_clarity": "Live presentation clarity",
    "live_understanding": "Live technical understanding",
    "live_delivery": "Live delivery",
    "live_qa": "Q&A handling",
    "live_coordination": "Team coordination",
    "always_innovation": "Innovation",
    "always_impact": "Impact",
}


def create_event(session: Session, request: EventCreateRequest) -> EvaluationEvent:
    event = EvaluationEvent(
        name=request.name.strip(),
        type=request.type,
        status=request.status,
        description=request.description,
        submission_deadline=request.submission_deadline,
        judging_deadline=request.judging_deadline or request.submission_deadline,
        artifacts=request.artifacts,
        criteria_config=request.criteria_config,
    )
    session.add(event)
    session.flush()

    assignment = Assignment(
        event_id=event.id,
        title=event.name,
        description=event.description,
        due_date=event.submission_deadline,
        is_active=True,
    )
    session.add(assignment)
    session.flush()

    for index, criterion in enumerate(_rubric_from_event_config(request.criteria_config)):
        session.add(
            RubricCriterion(
                assignment_id=assignment.id,
                category=criterion["category"],
                description=criterion["description"],
                max_score=criterion["max_score"],
                sort_order=index,
            )
        )

    session.commit()
    session.refresh(event)
    return event


def list_events(session: Session, settings: Settings) -> list[EventResponse]:
    statement: Select[tuple[EvaluationEvent]] = select(EvaluationEvent).order_by(
        EvaluationEvent.created_at.desc()
    )
    return [build_event_response(session, event, settings) for event in session.scalars(statement)]


def get_event(session: Session, event_id: str) -> EvaluationEvent | None:
    return session.get(EvaluationEvent, event_id)


def delete_event(session: Session, event: EvaluationEvent) -> None:
    session.delete(event)
    session.commit()


def build_event_response(session: Session, event: EvaluationEvent, settings: Settings) -> EventResponse:
    teams_total = session.scalar(
        select(func.count(Submission.id)).where(Submission.event_id == event.id)
    ) or 0
    teams_evaluated = session.scalar(
        select(func.count(Submission.id)).where(
            Submission.event_id == event.id,
            Submission.status == "completed",
        )
    ) or 0

    frontend_base_url = (settings.frontend_url or "http://localhost:3000").rstrip("/")
    student_submit_url = f"{frontend_base_url}/events/{event.id}/submit"

    
    return EventResponse(
        id=event.id,
        name=event.name,
        type=event.type,
        status=event.status,
        description=event.description,
        submission_deadline=event.submission_deadline,
        judging_deadline=event.judging_deadline,
        artifacts=event.artifacts or [],
        criteria_config=event.criteria_config or {},
        student_submit_url=student_submit_url,
        teams_total=teams_total,
        teams_evaluated=teams_evaluated,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _rubric_from_event_config(criteria_config: dict[str, Any]) -> list[dict[str, Any]]:
    rubric: list[dict[str, Any]] = []
    criteria = criteria_config.get("criteria", criteria_config)

    if not isinstance(criteria, dict):
        return rubric

    for criterion_id, state in criteria.items():
        if not isinstance(state, dict) or not state.get("selected", False):
            continue

        weight = float(state.get("weight") or 0)

        if weight <= 0:
            continue

        category = state.get("label") or CRITERION_LABELS.get(
            criterion_id,
            str(criterion_id).replace("_", " ").title(),
        )

        description = state.get("description") or f"Evaluate {str(category).lower()} for this submission."

        rubric.append(
            {
                "category": str(category),
                "description": str(description),
                "max_score": weight,
            }
        )

    return rubric