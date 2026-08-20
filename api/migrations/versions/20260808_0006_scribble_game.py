"""Add the Scribble drawing and guessing game."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0006_scribble_game"
down_revision: str | Sequence[str] | None = "20260808_0005"
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
        "name": "Scribble", "players": "2–4 players", "icon": "✏️",
        "color": "coral", "is_featured": True,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'Scribble'"))
