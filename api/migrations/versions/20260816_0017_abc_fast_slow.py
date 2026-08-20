"""Add ABC Fast or Slow to the playable game catalog."""
import sqlalchemy as sa
from alembic import op

revision = "20260816_0017"
down_revision = "20260815_0016"
branch_labels = None
depends_on = None

def upgrade() -> None:
    games = sa.table("games", sa.column("name", sa.String()), sa.column("players", sa.String()), sa.column("icon", sa.String()), sa.column("color", sa.String()), sa.column("is_featured", sa.Boolean()))
    op.bulk_insert(games, [{"name": "ABC Fast or Slow", "players": "2–6 players", "icon": "🔤", "color": "sage", "is_featured": True}])

def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'ABC Fast or Slow'"))
