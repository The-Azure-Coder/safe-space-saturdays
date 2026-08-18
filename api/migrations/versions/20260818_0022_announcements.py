"""Add community announcements."""

import sqlalchemy as sa
from alembic import op


revision = "20260818_0022"
down_revision = "20260818_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cta_label", sa.String(length=80), nullable=True),
        sa.Column("cta_path", sa.String(length=200), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_announcements_author_id", "announcements", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_announcements_author_id", table_name="announcements")
    op.drop_table("announcements")
