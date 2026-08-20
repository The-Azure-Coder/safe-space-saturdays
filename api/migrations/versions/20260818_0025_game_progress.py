"""Track per-game levels and win streaks."""

import sqlalchemy as sa
from alembic import op

revision = "20260818_0025"
down_revision = "20260818_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_type", sa.String(length=30), nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("best_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.UniqueConstraint("user_id", "game_type", name="uq_game_progress_user_game"),
    )
    op.create_index("ix_game_progress_user_id", "game_progress", ["user_id"])
    op.create_index("ix_game_progress_game_type", "game_progress", ["game_type"])


def downgrade() -> None:
    op.drop_index("ix_game_progress_game_type", table_name="game_progress")
    op.drop_index("ix_game_progress_user_id", table_name="game_progress")
    op.drop_table("game_progress")
