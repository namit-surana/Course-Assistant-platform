"""Add events, courses, teams, users, and overrides.

Revision ID: 20260501_0002
Revises: 20260501_0001
Create Date: 2026-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260501_0002"
down_revision = "20260501_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("cognito_sub", sa.String(length=255), nullable=True),
        sa.Column("auth_provider", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cognito_sub"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("invite_code", sa.String(length=80), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_table(
        "evaluation_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("course_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("submission_deadline", sa.Date(), nullable=True),
        sa.Column("judging_deadline", sa.Date(), nullable=True),
        sa.Column("artifacts", sa.JSON(), nullable=True),
        sa.Column("criteria_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "course_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("course_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("invite_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_table(
        "team_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("assignments", sa.Column("course_id", sa.String(length=36), nullable=True))
    op.add_column("assignments", sa.Column("event_id", sa.String(length=36), nullable=True))
    op.add_column("assignments", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("assignments", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.create_foreign_key("fk_assignments_course_id", "assignments", "courses", ["course_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_assignments_event_id", "assignments", "evaluation_events", ["event_id"], ["id"], ondelete="SET NULL")
    op.add_column("submissions", sa.Column("event_id", sa.String(length=36), nullable=True))
    op.add_column("submissions", sa.Column("team_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_submissions_event_id", "submissions", "evaluation_events", ["event_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_submissions_team_id", "submissions", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "feedback_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("feedback_score_id", sa.String(length=36), nullable=False),
        sa.Column("overridden_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("original_score", sa.Numeric(8, 2), nullable=False),
        sa.Column("override_score", sa.Numeric(8, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["feedback_score_id"], ["feedback_scores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["overridden_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_events_status_created_at", "evaluation_events", ["status", "created_at"])
    op.create_index("ix_submissions_event_created_at", "submissions", ["event_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_submissions_event_created_at", table_name="submissions")
    op.drop_index("ix_evaluation_events_status_created_at", table_name="evaluation_events")
    op.drop_table("feedback_overrides")
    op.drop_constraint("fk_submissions_team_id", "submissions", type_="foreignkey")
    op.drop_constraint("fk_submissions_event_id", "submissions", type_="foreignkey")
    op.drop_column("submissions", "team_id")
    op.drop_column("submissions", "event_id")
    op.drop_constraint("fk_assignments_event_id", "assignments", type_="foreignkey")
    op.drop_constraint("fk_assignments_course_id", "assignments", type_="foreignkey")
    op.drop_column("assignments", "is_active")
    op.drop_column("assignments", "due_date")
    op.drop_column("assignments", "event_id")
    op.drop_column("assignments", "course_id")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("course_members")
    op.drop_table("evaluation_events")
    op.drop_table("courses")
    op.drop_table("users")
