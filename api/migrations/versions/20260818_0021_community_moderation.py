"""Add community moderation state and posting timeouts."""

import sqlalchemy as sa
from alembic import op


revision = "20260818_0021"
down_revision = "20260816_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("posting_timeout_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column("is_flagged", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("posts", "is_flagged")
    op.drop_column("users", "posting_timeout_until")
