"""Add analysis_jobs.job_type for artifact-specific dispatch.

Revision ID: 20260505_0004
Revises: 20260505_0003
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_0004"
down_revision = "20260505_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "job_type",
            sa.String(length=40),
            nullable=False,
            server_default="submission_analysis",
        ),
    )
    op.create_check_constraint(
        "ck_analysis_jobs_job_type",
        "analysis_jobs",
        "job_type IN ('submission_analysis','git_analysis','ppt_analysis','video_analysis')",
    )
    op.alter_column("analysis_jobs", "job_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_analysis_jobs_job_type", "analysis_jobs", type_="check")
    op.drop_column("analysis_jobs", "job_type")
