"""Add analysis_jobs.result_json for per-agent result storage.

Revision ID: 20260507_0006
Revises: 20260506_0005
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260507_0006"
down_revision = "20260506_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analysis_jobs", "result_json")

