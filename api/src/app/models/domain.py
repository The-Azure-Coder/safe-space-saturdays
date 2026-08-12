from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    google_subject: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member", server_default="member")
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class BugReport(TimestampMixin, Base):
    __tablename__ = "bug_reports"
    __table_args__ = (Index("ix_bug_reports_status_created", "status", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal")
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Quote(TimestampMixin, Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(120), default="Unknown", server_default="Unknown")
    category: Mapped[str] = mapped_column(String(40), index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approval_status: Mapped[str] = mapped_column(String(20), default="approved", server_default="approved", index=True)
    submitted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)


class SavedQuote(Base):
    __tablename__ = "saved_quotes"
    __table_args__ = (UniqueConstraint("user_id", "quote_id", name="uq_saved_quote_user_quote"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"))


class CheckIn(TimestampMixin, Base):
    __tablename__ = "check_ins"
    __table_args__ = (Index("ix_check_ins_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mood: Mapped[str] = mapped_column(String(30))
    needs: Mapped[list[str]] = mapped_column(JSON, default=list)
    energy: Mapped[int] = mapped_column(Integer)
    stress: Mapped[int] = mapped_column(Integer)
    thoughts: Mapped[str | None] = mapped_column(Text, nullable=True)
    gratitude: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_created", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    post_type: Mapped[str] = mapped_column(String(30), default="original", server_default="original")
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id", ondelete="SET NULL"), nullable=True, index=True)


class PostReaction(Base):
    __tablename__ = "post_reactions"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", "kind", name="uq_post_reaction"),
        CheckConstraint("kind IN ('like', 'dislike', 'love')", name="ck_post_reaction_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)


class Game(TimestampMixin, Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    players: Mapped[str] = mapped_column(String(40))
    icon: Mapped[str] = mapped_column(String(8))
    color: Mapped[str] = mapped_column(String(20))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class GameRoom(TimestampMixin, Base):
    __tablename__ = "game_rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    max_players: Mapped[int] = mapped_column(Integer, default=4, server_default="4")
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    fill_with_bots: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    invite_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bot_difficulty: Mapped[str] = mapped_column(
        String(20), default="friendly", server_default="friendly"
    )


class RoomParticipant(Base):
    __tablename__ = "room_participants"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_participant"),
        UniqueConstraint("room_id", "seat_index", name="uq_room_participant_seat"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("game_rooms.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    seat_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ready: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GameWinner(TimestampMixin, Base):
    __tablename__ = "game_winners"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    result: Mapped[str] = mapped_column(String(160))


class GameMatch(TimestampMixin, Base):
    __tablename__ = "game_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("game_rooms.id", ondelete="CASCADE"), index=True
    )
    game_type: Mapped[str] = mapped_column(String(30), index=True)
    player_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")


class GameMatchPlayer(Base):
    __tablename__ = "game_match_players"
    __table_args__ = (
        UniqueConstraint("match_id", "seat_index", name="uq_game_match_player_seat"),
        UniqueConstraint("match_id", "user_id", name="uq_game_match_player_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(
        ForeignKey("game_matches.id", ondelete="CASCADE"), index=True
    )
    seat_index: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    player_type: Mapped[str] = mapped_column(String(10), default="human", server_default="human")
    display_name: Mapped[str] = mapped_column(String(120))
    bot_difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)


class GameEvent(Base):
    __tablename__ = "game_events"
    __table_args__ = (
        UniqueConstraint("match_id", "sequence", name="uq_game_event_match_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[str] = mapped_column(
        ForeignKey("game_matches.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[dict[str, Any]] = mapped_column(JSON)
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RewardLedger(TimestampMixin, Base):
    __tablename__ = "reward_ledger"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_reward_ledger_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    match_id: Mapped[str] = mapped_column(
        ForeignKey("game_matches.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    xp: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
