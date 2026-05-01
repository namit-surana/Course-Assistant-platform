from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models import Assignment, RubricCriterion
from src.events.schemas import EventCreateRequest
from src.events.service import build_event_response, create_event


def test_create_event_persists_assignment_and_rubric() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    with session_factory() as session:
        event = create_event(
            session,
            EventCreateRequest(
                name="Final Project",
                type="course",
                submission_deadline="2026-05-15",
                artifacts=["repo", "presentation"],
                criteria_config={
                    "criteria": {
                        "repo_code_quality": {"selected": True, "weight": 40},
                        "pres_clarity": {"selected": True, "weight": 60},
                        "demo_quality": {"selected": False, "weight": 100},
                    }
                },
            ),
        )

        assignment = session.query(Assignment).filter_by(event_id=event.id).one()
        rubric = (
            session.query(RubricCriterion)
            .filter_by(assignment_id=assignment.id)
            .order_by(RubricCriterion.sort_order)
            .all()
        )
        response = build_event_response(session, event)

        assert response.name == "Final Project"
        assert response.teams_total == 0
        assert assignment.title == "Final Project"
        assert [item.category for item in rubric] == ["Code quality", "Presentation clarity"]
