"""Allow final_grading_analysis as analysis job type.

Revision ID: 20260507_0007
Revises: 20260507_0006
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


revision = "20260507_0007"
down_revision = "20260507_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_analysis_jobs_job_type", "analysis_jobs", type_="check")
    op.create_check_constraint(
        "ck_analysis_jobs_job_type",
        "analysis_jobs",
        "job_type IN ('submission_analysis','git_analysis','ppt_analysis','video_analysis','final_grading_analysis')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_analysis_jobs_job_type", "analysis_jobs", type_="check")
    op.create_check_constraint(
        "ck_analysis_jobs_job_type",
        "analysis_jobs",
        "job_type IN ('submission_analysis','git_analysis','ppt_analysis','video_analysis')",
    )

