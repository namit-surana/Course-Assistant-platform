from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


def _uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    cognito_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    auth_provider: Mapped[str | None] = mapped_column(String(80))

    course_memberships: Mapped[list[CourseMember]] = relationship(back_populates="user")
    team_memberships: Mapped[list[TeamMember]] = relationship(back_populates="user")


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    invite_code: Mapped[str | None] = mapped_column(String(80), unique=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    members: Mapped[list[CourseMember]] = relationship(back_populates="course")
    teams: Mapped[list[Team]] = relationship(back_populates="course")
    assignments: Mapped[list[Assignment]] = relationship(back_populates="course")
    events: Mapped[list[EvaluationEvent]] = relationship(back_populates="course")


class CourseMember(TimestampMixin, Base):
    __tablename__ = "course_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)

    course: Mapped[Course] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="course_memberships")


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(80), unique=True)

    course: Mapped[Course | None] = relationship(back_populates="teams")
    members: Mapped[list[TeamMember]] = relationship(back_populates="team")
    submissions: Mapped[list[Submission]] = relationship(back_populates="team")


class TeamMember(TimestampMixin, Base):
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(40), default="student", nullable=False)

    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="team_memberships")


class EvaluationEvent(TimestampMixin, Base):
    __tablename__ = "evaluation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    submission_deadline: Mapped[datetime | None] = mapped_column(Date)
    judging_deadline: Mapped[datetime | None] = mapped_column(Date)
    artifacts: Mapped[list[str] | None] = mapped_column(JSON)
    criteria_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    course: Mapped[Course | None] = relationship(back_populates="events")
    assignments: Mapped[list[Assignment]] = relationship(back_populates="event")
    submissions: Mapped[list[Submission]] = relationship(back_populates="event")


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("evaluation_events.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[datetime | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    course: Mapped[Course | None] = relationship(back_populates="assignments")
    event: Mapped[EvaluationEvent | None] = relationship(back_populates="assignments")
    rubric_criteria: Mapped[list[RubricCriterion]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list[Submission]] = relationship(back_populates="assignment")


class RubricCriterion(TimestampMixin, Base):
    __tablename__ = "rubric_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    assignment: Mapped[Assignment] = relationship(back_populates="rubric_criteria")


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("evaluation_events.id", ondelete="SET NULL")
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="SET NULL"),
    )
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
    )
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    submitter_email: Mapped[str | None] = mapped_column(String(320))
    repo_url: Mapped[str | None] = mapped_column(Text)
    branch: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    rubric_snapshot: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    event: Mapped[EvaluationEvent | None] = relationship(back_populates="submissions")
    assignment: Mapped[Assignment | None] = relationship(back_populates="submissions")
    team: Mapped[Team | None] = relationship(back_populates="submissions")
    artifacts: Mapped[list[SubmissionArtifact]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    analysis_jobs: Mapped[list[AnalysisJob]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    feedback_report: Mapped[FeedbackReport | None] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class SubmissionArtifact(TimestampMixin, Base):
    __tablename__ = "submission_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="artifacts")


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    sqs_message_id: Mapped[str | None] = mapped_column(String(255))
    job_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    submission: Mapped[Submission] = relationship(back_populates="analysis_jobs")


class FeedbackReport(TimestampMixin, Base):
    __tablename__ = "feedback_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text)
    raw_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    submission: Mapped[Submission] = relationship(back_populates="feedback_report")
    scores: Mapped[list[FeedbackScore]] = relationship(
        back_populates="feedback_report",
        cascade="all, delete-orphan",
    )


class FeedbackScore(TimestampMixin, Base):
    __tablename__ = "feedback_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    feedback_report_id: Mapped[str] = mapped_column(
        ForeignKey("feedback_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    max_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    comment: Mapped[str | None] = mapped_column(Text)

    feedback_report: Mapped[FeedbackReport] = relationship(back_populates="scores")


class FeedbackOverride(TimestampMixin, Base):
    __tablename__ = "feedback_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    feedback_score_id: Mapped[str] = mapped_column(
        ForeignKey("feedback_scores.id", ondelete="CASCADE"),
        nullable=False,
    )
    overridden_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    original_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    override_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


Index("ix_evaluation_events_status_created_at", EvaluationEvent.status, EvaluationEvent.created_at)
Index("ix_submissions_status_created_at", Submission.status, Submission.created_at)
Index("ix_submissions_event_created_at", Submission.event_id, Submission.created_at)
Index("ix_analysis_jobs_status_created_at", AnalysisJob.status, AnalysisJob.created_at)
Index("ix_submission_artifacts_submission_kind", SubmissionArtifact.submission_id, SubmissionArtifact.kind)
