"""Add user-submitted bug reports for the admin workflow."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_0006"
down_revision: str | Sequence[str] | None = "20260806_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bug_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), server_default="normal", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bug_reports_user_id", "bug_reports", ["user_id"])
    op.create_index("ix_bug_reports_status_created", "bug_reports", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("bug_reports")
