"""Add weekly wellbeing challenges and idempotent completions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0013"
down_revision: str | Sequence[str] | None = "20260812_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("icon", sa.String(8), nullable=False),
        sa.Column("color", sa.String(20), nullable=False),
        sa.Column("xp", sa.Integer(), server_default="15", nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("active_until", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("week_start", "slug", name="uq_challenges_week_slug"),
        sa.CheckConstraint("xp BETWEEN 1 AND 100", name="ck_challenges_xp_range"),
    )
    op.create_index("ix_challenges_week_start", "challenges", ["week_start"])
    op.create_index("ix_challenges_active_until", "challenges", ["active_until"])
    op.create_index("ix_challenges_week_active", "challenges", ["week_start", "active_until"])

    op.create_table(
        "challenge_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reflection", sa.String(500), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("challenge_id", "user_id", name="uq_challenge_completion_user"),
        sa.CheckConstraint(
            "xp_awarded >= 0", name="ck_challenge_completions_xp_nonnegative"
        ),
    )
    op.create_index(
        "ix_challenge_completions_challenge_id", "challenge_completions", ["challenge_id"]
    )
    op.create_index("ix_challenge_completions_user_id", "challenge_completions", ["user_id"])
    op.create_index(
        "ix_challenge_completions_user_created",
        "challenge_completions",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_challenge_completions_user_created", table_name="challenge_completions")
    op.drop_index("ix_challenge_completions_user_id", table_name="challenge_completions")
    op.drop_index("ix_challenge_completions_challenge_id", table_name="challenge_completions")
    op.drop_table("challenge_completions")
    op.drop_index("ix_challenges_week_active", table_name="challenges")
    op.drop_index("ix_challenges_active_until", table_name="challenges")
    op.drop_index("ix_challenges_week_start", table_name="challenges")
    op.drop_table("challenges")
