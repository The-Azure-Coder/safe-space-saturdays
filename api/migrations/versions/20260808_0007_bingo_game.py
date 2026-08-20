"""Add Bingo to the playable game catalog."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0007_bingo_game"
down_revision: str | Sequence[str] | None = "20260808_0006_scribble_game"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    games = sa.table(
        "games",
        sa.column("name", sa.String()),
        sa.column("players", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("color", sa.String()),
        sa.column("is_featured", sa.Boolean()),
    )
    op.bulk_insert(games, [{
        "name": "Bingo", "players": "2–8 players", "icon": "🎯",
        "color": "peach", "is_featured": True,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'Bingo'"))
