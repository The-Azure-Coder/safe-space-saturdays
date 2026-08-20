"""Remove Bingo from the active game catalog.

Existing Bingo matches remain readable through their persisted game type, but
new users will no longer see or create Bingo rooms from the catalog.
"""

import sqlalchemy as sa
from alembic import op


revision = "20260816_0018"
down_revision = "20260816_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'Bingo'"))


def downgrade() -> None:
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
        [{
            "name": "Bingo",
            "players": "2–8 players",
            "icon": "🎯",
            "color": "peach",
            "is_featured": True,
        }],
    )
