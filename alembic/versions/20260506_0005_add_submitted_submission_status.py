"""Allow 'submitted' as a submission status.

Revision ID: 20260506_0005
Revises: 20260505_0004
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op


revision = "20260506_0005"
down_revision = "20260505_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_submissions_status", "submissions", type_="check")
    op.create_check_constraint(
        "ck_submissions_status",
        "submissions",
        "status IN ('submitted','queued','running','completed','failed')",
    )
    op.execute("UPDATE submissions SET status='submitted' WHERE status='queued'")
    op.alter_column("submissions", "status", server_default="submitted")


def downgrade() -> None:
    op.alter_column("submissions", "status", server_default="queued")
    op.execute("UPDATE submissions SET status='queued' WHERE status='submitted'")
    op.drop_constraint("ck_submissions_status", "submissions", type_="check")
    op.create_check_constraint(
        "ck_submissions_status",
        "submissions",
        "status IN ('queued','running','completed','failed')",
    )

