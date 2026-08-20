"""Add Checkers to the playable game catalogue."""

import sqlalchemy as sa
from alembic import op

revision = "20260818_0023"
down_revision = "20260818_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    games = sa.table(
        "games",
        sa.column("name", sa.String()),
        sa.column("players", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("color", sa.String()),
        sa.column("is_featured", sa.Boolean()),
    )
    op.bulk_insert(
        games,
        [{"name": "Checkers", "players": "2 players", "icon": "♟", "color": "coral", "is_featured": True}],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'Checkers'"))
