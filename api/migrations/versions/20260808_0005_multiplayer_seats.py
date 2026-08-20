"""Persist room readiness and match seats for human multiplayer."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260808_0005"
down_revision: str | Sequence[str] | None = "20260806_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("game_rooms", sa.Column("fill_with_bots", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("game_rooms", sa.Column("bot_difficulty", sa.String(20), server_default="friendly", nullable=False))
    op.add_column("room_participants", sa.Column("seat_index", sa.Integer(), nullable=True))
    op.add_column("room_participants", sa.Column("ready", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("room_participants", sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_unique_constraint("uq_room_participant_seat", "room_participants", ["room_id", "seat_index"])
    op.create_table(
        "game_match_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("game_matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seat_index", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("player_type", sa.String(10), server_default="human", nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("bot_difficulty", sa.String(20), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.UniqueConstraint("match_id", "seat_index", name="uq_game_match_player_seat"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_game_match_player_user"),
    )
    op.create_index("ix_game_match_players_match_id", "game_match_players", ["match_id"])
    op.create_index("ix_game_match_players_user_id", "game_match_players", ["user_id"])


def downgrade() -> None:
    op.drop_table("game_match_players")
    op.drop_constraint("uq_room_participant_seat", "room_participants", type_="unique")
    op.drop_column("room_participants", "joined_at")
    op.drop_column("room_participants", "ready")
    op.drop_column("room_participants", "seat_index")
    op.drop_column("game_rooms", "bot_difficulty")
    op.drop_column("game_rooms", "fill_with_bots")
