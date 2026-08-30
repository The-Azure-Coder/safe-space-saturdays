"""Add the private CSEC IT mock exam game."""

from alembic import op
import sqlalchemy as sa

revision = "20260830_0028"
down_revision = "20260830_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    games = sa.table(
        "games", sa.column("name", sa.String()), sa.column("players", sa.String()),
        sa.column("icon", sa.String()), sa.column("color", sa.String()), sa.column("is_featured", sa.Boolean()),
    )
    op.bulk_insert(games, [{
        "name": "CSEC IT Mock Exam", "players": "1–2 players",
        "icon": "📝", "color": "coral", "is_featured": True,
    }])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'CSEC IT Mock Exam'"))
