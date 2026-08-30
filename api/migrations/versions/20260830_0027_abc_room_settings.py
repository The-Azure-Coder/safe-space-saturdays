"""Add host-configurable ABC room settings."""

import sqlalchemy as sa
from alembic import op

revision = "20260830_0027"
down_revision = "20260822_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("game_rooms", sa.Column("abc_categories", sa.JSON(), nullable=True))
    op.add_column(
        "game_rooms",
        sa.Column("abc_majority_invalid", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("game_rooms", "abc_majority_invalid")
    op.drop_column("game_rooms", "abc_categories")
