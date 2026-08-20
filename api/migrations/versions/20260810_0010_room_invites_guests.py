"""Add secure room invites and temporary guest participants."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260810_0010"
down_revision: str | Sequence[str] | None = "20260809_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_guest", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("game_rooms", sa.Column("invite_token", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE game_rooms SET invite_token = md5(random()::text || clock_timestamp()::text) WHERE invite_token IS NULL"))
    op.alter_column("game_rooms", "invite_token", nullable=False)
    op.create_index("ix_game_rooms_invite_token", "game_rooms", ["invite_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_game_rooms_invite_token", table_name="game_rooms")
    op.drop_column("game_rooms", "invite_token")
    op.drop_column("users", "is_guest")
