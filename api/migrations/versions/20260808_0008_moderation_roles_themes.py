"""Add moderation workflow, staff roles, approval gate, and shared quote metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260808_0008"
down_revision: str | Sequence[str] | None = "20260808_0007_bingo_game"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_approved", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("quotes", sa.Column("approval_status", sa.String(20), server_default="approved", nullable=False))
    op.add_column("quotes", sa.Column("submitted_by_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_quotes_submitted_by_user", "quotes", "users", ["submitted_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_quotes_approval_status", "quotes", ["approval_status"])
    op.create_index("ix_quotes_submitted_by_user_id", "quotes", ["submitted_by_user_id"])
    op.add_column("posts", sa.Column("post_type", sa.String(30), server_default="original", nullable=False))
    op.add_column("posts", sa.Column("quote_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_posts_quote", "posts", "quotes", ["quote_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_posts_quote_id", "posts", ["quote_id"])


def downgrade() -> None:
    op.drop_index("ix_posts_quote_id", table_name="posts")
    op.drop_constraint("fk_posts_quote", "posts", type_="foreignkey")
    op.drop_column("posts", "quote_id")
    op.drop_column("posts", "post_type")
    op.drop_index("ix_quotes_submitted_by_user_id", table_name="quotes")
    op.drop_index("ix_quotes_approval_status", table_name="quotes")
    op.drop_constraint("fk_quotes_submitted_by_user", "quotes", type_="foreignkey")
    op.drop_column("quotes", "submitted_by_user_id")
    op.drop_column("quotes", "approval_status")
    op.drop_column("users", "is_approved")
