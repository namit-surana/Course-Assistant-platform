"""Harden integrity with unique and check constraints.

Revision ID: 20260505_0003
Revises: 20260501_0002
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_0003"
down_revision = "20260501_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # De-duplicate rows before introducing unique constraints.
    op.execute(
        """
        DELETE FROM course_members
        WHERE id IN (
          SELECT id
          FROM (
            SELECT
              id,
              ROW_NUMBER() OVER (
                PARTITION BY course_id, user_id
                ORDER BY created_at, id
              ) AS rn
            FROM course_members
          ) ranked
          WHERE ranked.rn > 1
        )
        """
    )
    op.execute(
        """
        DELETE FROM team_members
        WHERE id IN (
          SELECT id
          FROM (
            SELECT
              id,
              ROW_NUMBER() OVER (
                PARTITION BY team_id, user_id
                ORDER BY created_at, id
              ) AS rn
            FROM team_members
          ) ranked
          WHERE ranked.rn > 1
        )
        """
    )
    op.execute(
        """
        DELETE FROM submission_artifacts
        WHERE id IN (
          SELECT id
          FROM (
            SELECT
              id,
              ROW_NUMBER() OVER (
                PARTITION BY submission_id, kind
                ORDER BY created_at DESC, id DESC
              ) AS rn
            FROM submission_artifacts
          ) ranked
          WHERE ranked.rn > 1
        )
        """
    )

    op.create_unique_constraint(
        "uq_course_members_course_user",
        "course_members",
        ["course_id", "user_id"],
    )
    op.create_unique_constraint(
        "uq_team_members_team_user",
        "team_members",
        ["team_id", "user_id"],
    )
    op.create_unique_constraint(
        "uq_submission_artifacts_submission_kind",
        "submission_artifacts",
        ["submission_id", "kind"],
    )

    op.create_check_constraint(
        "ck_course_members_role",
        "course_members",
        "role IN ('student','ta','professor','instructor','owner')",
    )
    op.create_check_constraint(
        "ck_team_members_role",
        "team_members",
        "role IN ('student','ta','lead','owner')",
    )
    op.create_check_constraint(
        "ck_submissions_status",
        "submissions",
        "status IN ('queued','running','completed','failed')",
    )
    op.create_check_constraint(
        "ck_analysis_jobs_status",
        "analysis_jobs",
        "status IN ('queued','running','completed','failed')",
    )
    op.create_check_constraint(
        "ck_submission_artifacts_kind",
        "submission_artifacts",
        "kind IN ('repo','ppt','video','live_audio','attachment')",
    )
    op.create_check_constraint(
        "ck_submission_artifacts_status",
        "submission_artifacts",
        "status IN ('submitted','processing','completed','failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_submission_artifacts_status", "submission_artifacts", type_="check")
    op.drop_constraint("ck_submission_artifacts_kind", "submission_artifacts", type_="check")
    op.drop_constraint("ck_analysis_jobs_status", "analysis_jobs", type_="check")
    op.drop_constraint("ck_submissions_status", "submissions", type_="check")
    op.drop_constraint("ck_team_members_role", "team_members", type_="check")
    op.drop_constraint("ck_course_members_role", "course_members", type_="check")

    op.drop_constraint(
        "uq_submission_artifacts_submission_kind",
        "submission_artifacts",
        type_="unique",
    )
    op.drop_constraint("uq_team_members_team_user", "team_members", type_="unique")
    op.drop_constraint("uq_course_members_course_user", "course_members", type_="unique")

