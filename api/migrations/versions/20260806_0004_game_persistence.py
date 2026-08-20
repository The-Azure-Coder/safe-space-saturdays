"""Persist game snapshots, events, and idempotent rewards."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_0004"
down_revision: str | Sequence[str] | None = "20260806_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("game_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_type", sa.String(30), nullable=False),
        sa.Column("player_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_game_matches_room_id", "game_matches", ["room_id"])
    op.create_index("ix_game_matches_game_type", "game_matches", ["game_type"])
    op.create_table(
        "game_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("game_matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("match_id", "sequence", name="uq_game_event_match_sequence"),
    )
    op.create_index("ix_game_events_match_id", "game_events", ["match_id"])
    op.create_table(
        "reward_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("game_matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_reward_ledger_idempotency"),
    )
    op.create_index("ix_reward_ledger_user_id", "reward_ledger", ["user_id"])
    op.create_index("ix_reward_ledger_match_id", "reward_ledger", ["match_id"])


def downgrade() -> None:
    op.drop_table("reward_ledger")
    op.drop_table("game_events")
    op.drop_table("game_matches")
