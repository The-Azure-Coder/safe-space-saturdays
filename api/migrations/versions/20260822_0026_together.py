"""Add Together rooms and catalog entry."""
from alembic import op
import sqlalchemy as sa

revision = "20260822_0026"
down_revision = "20260818_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("game_rooms", sa.Column("room_code", sa.String(length=10), nullable=True))
    op.create_index("ix_game_rooms_room_code", "game_rooms", ["room_code"], unique=True)
    op.execute(sa.text(
        "INSERT INTO games (name, players, icon, color, is_featured) "
        "VALUES ('Together', '2–4 players', '🤝', 'lilac', true) "
        "ON CONFLICT (name) DO NOTHING"
    ))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM games WHERE name = 'Together'"))
    op.drop_index("ix_game_rooms_room_code", table_name="game_rooms")
    op.drop_column("game_rooms", "room_code")
