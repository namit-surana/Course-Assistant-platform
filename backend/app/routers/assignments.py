from fastapi import APIRouter

router = APIRouter()

# TODO: POST   /courses/{course_id}/assignments    — create assignment (professor)
# TODO: GET    /courses/{course_id}/assignments    — list assignments for course
# TODO: GET    /{id}                               — get assignment + rubric
# TODO: POST   /{id}/rubric                        — add rubric criterion (professor)
# TODO: PATCH  /{id}/rubric/{criteria_id}          — update criterion
# TODO: DELETE /{id}/rubric/{criteria_id}          — delete criterion
# TODO: GET    /{id}/results                       — all team scores (professor/TA)
# TODO: GET    /{id}/export                        — CSV export
