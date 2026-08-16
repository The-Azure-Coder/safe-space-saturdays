"""Preserve rewards when a finished game room is deleted."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0016"
down_revision: str | None = "20260814_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("reward_ledger", "match_id", existing_type=sa.String(length=36), nullable=True)
    op.drop_constraint("reward_ledger_match_id_fkey", "reward_ledger", type_="foreignkey")
    op.create_foreign_key(
        "reward_ledger_match_id_fkey",
        "reward_ledger",
        "game_matches",
        ["match_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("reward_ledger_match_id_fkey", "reward_ledger", type_="foreignkey")
    op.create_foreign_key(
        "reward_ledger_match_id_fkey",
        "reward_ledger",
        "game_matches",
        ["match_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("reward_ledger", "match_id", existing_type=sa.String(length=36), nullable=False)
