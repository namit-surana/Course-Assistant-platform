from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
import types

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.db.base import Base
from src.db.models import AnalysisJob, Submission, SubmissionArtifact

if "pptx" not in sys.modules:
    pptx_stub = types.ModuleType("pptx")
    pptx_stub.Presentation = object
    sys.modules["pptx"] = pptx_stub

from src.worker.processor import (
    _maybe_enqueue_final_grading_job,
    _normalize_criteria_config_for_final_grading,
)


def _seed_component_jobs(session: Session, submission_id: str, now: datetime) -> None:
    session.add_all(
        [
            AnalysisJob(
                submission_id=submission_id,
                job_type="git_analysis",
                status="completed",
                result_json={"repository": {"repository_analysis": {"executive_summary": "ok"}}},
                created_at=now - timedelta(seconds=3),
                updated_at=now - timedelta(seconds=3),
            ),
            AnalysisJob(
                submission_id=submission_id,
                job_type="ppt_analysis",
                status="completed",
                result_json={"ppt": {"ppt_summary": "ok"}},
                created_at=now - timedelta(seconds=2),
                updated_at=now - timedelta(seconds=2),
            ),
            AnalysisJob(
                submission_id=submission_id,
                job_type="video_analysis",
                status="completed",
                result_json={"video": {"parsed": {"summary": "ok"}}},
                created_at=now - timedelta(seconds=1),
                updated_at=now - timedelta(seconds=1),
            ),
        ]
    )


def test_auto_trigger_creates_final_grading_job_when_components_terminal() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, sqs_queue_url=None)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        submission = Submission(id="sub-trigger", team_name="Team Trigger", status="running")
        session.add(submission)
        session.flush()
        _seed_component_jobs(session, submission.id, now)
        session.flush()

        _maybe_enqueue_final_grading_job(
            session,
            submission.id,
            settings,
            triggering_job_type="git_analysis",
        )
        session.commit()

        final_jobs = list(
            session.scalars(
                select(AnalysisJob).where(
                    AnalysisJob.submission_id == submission.id,
                    AnalysisJob.job_type == "final_grading_analysis",
                )
            )
        )
        assert len(final_jobs) == 1
        assert final_jobs[0].status == "queued"


def test_auto_trigger_skips_when_final_is_already_fresh() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, sqs_queue_url=None)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        submission = Submission(id="sub-no-dup", team_name="Team No Dup", status="completed")
        session.add(submission)
        session.flush()
        _seed_component_jobs(session, submission.id, now - timedelta(seconds=10))
        session.add(
            AnalysisJob(
                submission_id=submission.id,
                job_type="final_grading_analysis",
                status="completed",
                result_json={"final_grading": {"overall_reasoning": "fresh"}},
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
        )
        session.flush()

        _maybe_enqueue_final_grading_job(
            session,
            submission.id,
            settings,
            triggering_job_type="video_analysis",
        )
        session.commit()

        final_jobs = list(
            session.scalars(
                select(AnalysisJob).where(
                    AnalysisJob.submission_id == submission.id,
                    AnalysisJob.job_type == "final_grading_analysis",
                )
            )
        )
        assert len(final_jobs) == 1


def test_auto_trigger_skips_when_any_component_not_completed() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, sqs_queue_url=None)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        submission = Submission(id="sub-not-all-complete", team_name="Team Incomplete", status="running")
        session.add(submission)
        session.flush()
        _seed_component_jobs(session, submission.id, now)
        pending_video = session.scalar(
            select(AnalysisJob).where(
                AnalysisJob.submission_id == submission.id,
                AnalysisJob.job_type == "video_analysis",
            )
        )
        assert pending_video is not None
        pending_video.status = "failed"
        pending_video.error_message = "video failed"
        pending_video.result_json = {"error": "video failed"}
        session.flush()

        _maybe_enqueue_final_grading_job(
            session,
            submission.id,
            settings,
            triggering_job_type="video_analysis",
        )
        session.commit()

        final_jobs = list(
            session.scalars(
                select(AnalysisJob).where(
                    AnalysisJob.submission_id == submission.id,
                    AnalysisJob.job_type == "final_grading_analysis",
                )
            )
        )
        assert len(final_jobs) == 0


def test_normalize_criteria_keeps_only_allowed_artifact_criteria() -> None:
    submission = Submission(id="sub-filter", team_name="Team Filter", status="submitted")
    submission.artifacts = [
        SubmissionArtifact(
            submission_id=submission.id,
            kind="repo",
            bucket="bucket",
            object_key="repo.zip",
            status="submitted",
        ),
        SubmissionArtifact(
            submission_id=submission.id,
            kind="ppt",
            bucket="bucket",
            object_key="slides.pptx",
            status="submitted",
        ),
    ]

    criteria_config = {
        "artifacts": ["repo", "presentation"],
        "criteria": {
            "repo_code_quality": {"selected": True, "weight": 40, "artifactId": "repo"},
            "pres_clarity": {"selected": True, "weight": 40, "artifactId": "presentation"},
            # Legacy orphan criterion from earlier wizard defaults (no artifactId)
            "report_problem": {"selected": True, "weight": 20},
            "always_innovation": {"selected": True, "weight": 20},
        },
    }

    normalized = _normalize_criteria_config_for_final_grading(criteria_config, submission)

    assert normalized["artifacts"] == ["presentation", "repo"]
    assert set(normalized["criteria"].keys()) == {
        "repo_code_quality",
        "pres_clarity",
    }
    assert "report_problem" not in normalized["criteria"]
    assert "always_innovation" not in normalized["criteria"]

