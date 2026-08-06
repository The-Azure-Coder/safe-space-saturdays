"""Create Safe Space Saturdays domain schema.

Revision ID: 20260805_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(20), server_default="member", nullable=False),
        sa.Column("xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("author", sa.String(120), server_default="Unknown", nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_quotes_category", "quotes", ["category"])
    op.create_table(
        "saved_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "quote_id", sa.Integer(), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
        ),
        sa.UniqueConstraint("user_id", "quote_id", name="uq_saved_quote_user_quote"),
    )
    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("mood", sa.String(30), nullable=False),
        sa.Column("needs", sa.JSON(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column("thoughts", sa.Text()),
        sa.Column("gratitude", sa.Text()),
        sa.Column("completed", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_check_ins_user_id", "check_ins", ["user_id"])
    op.create_index("ix_check_ins_user_created", "check_ins", ["user_id", "created_at"])
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_posts_user_id", "posts", ["user_id"])
    op.create_index("ix_posts_created", "posts", ["created_at"])
    op.create_table(
        "post_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.UniqueConstraint("post_id", "user_id", "kind", name="uq_post_reaction"),
    )
    op.create_index("ix_post_reactions_post_id", "post_reactions", ["post_id"])
    op.create_index("ix_post_reactions_user_id", "post_reactions", ["user_id"])
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("players", sa.String(40), nullable=False),
        sa.Column("icon", sa.String(8), nullable=False),
        sa.Column("color", sa.String(20), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "game_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "host_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("max_players", sa.Integer(), server_default="4", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_game_rooms_game_id", "game_rooms", ["game_id"])
    op.create_table(
        "room_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("game_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_participant"),
    )
    op.create_index("ix_room_participants_room_id", "room_participants", ["room_id"])
    op.create_index("ix_room_participants_user_id", "room_participants", ["user_id"])
    op.create_table(
        "game_winners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("result", sa.String(160), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.bulk_insert(
        sa.table(
            "quotes",
            sa.column("text", sa.Text()),
            sa.column("author", sa.String()),
            sa.column("category", sa.String()),
            sa.column("is_featured", sa.Boolean()),
        ),
        [
            {
                "text": "You don’t have to have it all figured out to move forward.",
                "author": "Unknown",
                "category": "Encouragement",
                "is_featured": True,
            },
            {
                "text": "Progress, not perfection. That’s enough.",
                "author": "Unknown",
                "category": "Growth",
                "is_featured": False,
            },
            {
                "text": "Be gentle with yourself. You’re doing your best.",
                "author": "Unknown",
                "category": "Rest",
                "is_featured": False,
            },
            {
                "text": "You are allowed to be both a work in progress and worthy of love.",
                "author": "Unknown",
                "category": "Connection",
                "is_featured": False,
            },
        ],
    )
    op.bulk_insert(
        sa.table(
            "games",
            sa.column("name", sa.String()),
            sa.column("players", sa.String()),
            sa.column("icon", sa.String()),
            sa.column("color", sa.String()),
            sa.column("is_featured", sa.Boolean()),
        ),
        [
            {
                "name": "Ludo",
                "players": "2–4 players",
                "icon": "🎲",
                "color": "sage",
                "is_featured": True,
            },
            {
                "name": "Dominoes",
                "players": "2–4 players",
                "icon": "🁣",
                "color": "peach",
                "is_featured": True,
            },
            {
                "name": "Trivia Battle",
                "players": "2+ players",
                "icon": "❔",
                "color": "lilac",
                "is_featured": True,
            },
            {
                "name": "Connect Four",
                "players": "2 players",
                "icon": "🔴",
                "color": "blue",
                "is_featured": True,
            },
        ],
    )


def downgrade() -> None:
    for table in (
        "game_winners",
        "room_participants",
        "game_rooms",
        "games",
        "comments",
        "post_reactions",
        "posts",
        "check_ins",
        "saved_quotes",
        "quotes",
        "sessions",
        "users",
    ):
        op.drop_table(table)
