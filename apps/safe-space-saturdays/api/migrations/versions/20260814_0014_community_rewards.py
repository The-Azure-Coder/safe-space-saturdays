"""Allow idempotent XP rewards for community posts."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260814_0014"
down_revision: str | None = "20260813_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("reward_ledger", "match_id", nullable=True)


def downgrade() -> None:
    op.alter_column("reward_ledger", "match_id", nullable=False)
