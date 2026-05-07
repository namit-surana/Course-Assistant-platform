from __future__ import annotations

from datetime import datetime, timezone

from src.db.models import AnalysisJob, Submission
from src.submissions.router import _build_feedback_response


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def test_feedback_response_prefers_completed_final_grading() -> None:
    submission = Submission(id="sub-1", team_name="Team A", status="completed")
    submission.analysis_jobs = [
        AnalysisJob(
            submission_id=submission.id,
            job_type="git_analysis",
            status="completed",
            result_json={"repository": {"repository_analysis": {"executive_summary": "Repo summary"}}},
            created_at=_ts(),
            updated_at=_ts(),
        ),
        AnalysisJob(
            submission_id=submission.id,
            job_type="final_grading_analysis",
            status="completed",
            result_json={
                "final_grading": {
                    "overall_score": 18,
                    "overall_max_score": 20,
                    "overall_reasoning": "Strong end-to-end delivery.",
                    "criterion_grades": [
                        {
                            "criterion": "Implementation Quality",
                            "score": 9,
                            "max_score": 10,
                            "reasoning": "Solid architecture and coding standards.",
                        }
                    ],
                }
            },
            created_at=_ts(),
            updated_at=_ts(),
        ),
    ]

    feedback = _build_feedback_response(submission)

    assert feedback is not None
    assert feedback.summary == "Strong end-to-end delivery."
    assert feedback.raw_result is not None
    assert "final_grading" in feedback.raw_result
    assert feedback.scores[0].category == "Implementation Quality"
    assert feedback.scores[0].score == 9


def test_feedback_response_falls_back_to_component_merge() -> None:
    submission = Submission(id="sub-2", team_name="Team B", status="completed")
    submission.analysis_jobs = [
        AnalysisJob(
            submission_id=submission.id,
            job_type="ppt_analysis",
            status="completed",
            result_json={"ppt": {"ppt_summary": "Presentation is clear and complete."}},
            created_at=_ts(),
            updated_at=_ts(),
        ),
    ]

    feedback = _build_feedback_response(submission)

    assert feedback is not None
    assert feedback.raw_result is not None
    assert feedback.raw_result.get("ppt", {}).get("ppt_summary") == "Presentation is clear and complete."
    assert feedback.summary == "Presentation is clear and complete."

