import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.games.connect_four import (
    ConnectFourState,
    IllegalMove,
    Player,
    apply_move,
    choose_bot_column,
    initial_state,
    serialize,
)


@dataclass
class LiveMatch:
    id: str
    room_id: int
    state: ConnectFourState = field(default_factory=initial_state)
    player_ids: dict[int, int] = field(default_factory=dict)
    bot_player: Player | None = None
    bot_difficulty: str = "friendly"
    reward_granted: bool = False
    sockets: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def snapshot(self) -> dict[str, Any]:
        return {
            "match_id": self.id,
            "room_id": self.room_id,
            "game": "connect-four",
            **serialize(self.state),
        }


class MatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, LiveMatch] = {}
        self.room_matches: dict[int, str] = {}

    def create(self, room_id: int, user_id: int, with_bot: bool, difficulty: str) -> LiveMatch:
        match = LiveMatch(id=str(uuid4()), room_id=room_id, player_ids={user_id: 1})
        if with_bot:
            match.bot_player = 2
            match.bot_difficulty = difficulty
        self.matches[match.id] = match
        self.room_matches[room_id] = match.id
        return match

    def get(self, match_id: str) -> LiveMatch | None:
        return self.matches.get(match_id)

    async def broadcast(self, match: LiveMatch, message: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []
        for socket in match.sockets:
            try:
                await socket.send_json(message)
            except Exception:
                disconnected.append(socket)
        for socket in disconnected:
            match.sockets.discard(socket)

    async def move(self, match: LiveMatch, user_id: int, column: int) -> dict[str, Any]:
        async with match.lock:
            stored_player = match.player_ids.get(user_id)
            if stored_player is None:
                raise IllegalMove("You are not a player in this match")
            player: Player = 1 if stored_player == 1 else 2
            match.state = apply_move(match.state, player, column)
            await self.broadcast(match, {"type": "state", "state": match.snapshot()})
            bot_turn = (
                match.bot_player == match.state.current_player
                and not match.state.winner
                and not match.state.draw
            )
            if bot_turn:
                bot_column = choose_bot_column(match.state, 2, match.bot_difficulty)
                match.state = apply_move(match.state, 2, bot_column)
                await self.broadcast(
                    match, {"type": "state", "state": match.snapshot(), "bot": True}
                )
            return match.snapshot()


match_manager = MatchManager()
