import asyncio
from dataclasses import dataclass, field
from dataclasses import replace
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
    game_level: int = 1
    game_streak: int = 0
    starting_player: Player = 1
    players: list[dict[str, Any]] = field(default_factory=list)
    reward_granted: bool = False
    sockets: dict[WebSocket, int] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    settlement_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def spectator_count(self) -> int:
        return sum(user_id not in self.player_ids for user_id in self.sockets.values())

    def snapshot(self, user_id: int | None = None) -> dict[str, Any]:
        player = self.player_ids.get(user_id, 1) if user_id is not None else None
        return {
            "match_id": self.id,
            "room_id": self.room_id,
            "game": "connect-four",
            **serialize(self.state),
            "player": player,
            "players": self.players,
            "game_level": getattr(self, "game_level", 1),
            "game_streak": getattr(self, "game_streak", 0),
            "spectator_count": self.spectator_count(),
        }


class MatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, LiveMatch] = {}
        self.room_matches: dict[int, str] = {}

    def create(
        self,
        room_id: int,
        user_id: int,
        with_bot: bool,
        difficulty: str,
        game_level: int = 1,
        game_streak: int = 0,
        player_ids: dict[int, int] | None = None,
        player_names: dict[int, str] | None = None,
    ) -> LiveMatch:
        match = LiveMatch(
            id=str(uuid4()),
            room_id=room_id,
            player_ids={user: seat + 1 for user, seat in (player_ids or {user_id: 0}).items()},
            game_level=game_level,
            game_streak=game_streak,
        )
        names = player_names or {}
        match.players = [
            {
                "name": names.get(seat, "You" if seat == 0 else "Milo Bot"),
                "is_bot": False,
            }
            for seat in range(2)
        ]
        match.bot_player = None
        # Bot filling only occupies an empty seat. Keep seat 2 human when a
        # second participant joined before the host started the room.
        if with_bot and 2 not in match.player_ids.values():
            match.bot_player = 2
            match.bot_difficulty = difficulty
            match.players[1]["is_bot"] = True
        self.matches[match.id] = match
        self.room_matches[room_id] = match.id
        return match

    def get(self, match_id: str) -> LiveMatch | None:
        return self.matches.get(match_id)

    async def broadcast(self, match: LiveMatch, message: dict[str, Any]) -> None:
        message = {**message, "spectator_count": match.spectator_count()}
        disconnected: list[WebSocket] = []
        for socket in list(match.sockets):
            try:
                await socket.send_json(message)
            except Exception:
                disconnected.append(socket)
        for socket in disconnected:
            match.sockets.pop(socket, None)

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
                await asyncio.sleep(0.55)
                bot_column = choose_bot_column(match.state, 2, match.bot_difficulty)
                match.state = apply_move(match.state, 2, bot_column)
                await self.broadcast(
                    match, {"type": "state", "state": match.snapshot(), "bot": True}
                )
            return match.snapshot(user_id)

    async def play_again(self, match: LiveMatch, user_id: int) -> dict[str, Any]:
        async with match.lock:
            if user_id not in match.player_ids:
                raise IllegalMove("You are not a player in this match")
            if not match.state.winner and not match.state.draw:
                raise IllegalMove("Finish the current game before playing again")
            match.starting_player = 2 if match.starting_player == 1 else 1
            match.state = initial_state()
            match.state = replace(match.state, current_player=match.starting_player)
            match.reward_granted = False
            if match.bot_player == match.state.current_player:
                await asyncio.sleep(0.55)
                bot_column = choose_bot_column(match.state, 2, match.bot_difficulty)
                match.state = apply_move(match.state, 2, bot_column)
            # Publish one authoritative reset after any bot opening move. This
            # prevents clients from briefly seeing an interactive empty board
            # before the bot has taken its alternating opening turn.
            await self.broadcast(match, {"type": "state", "state": match.snapshot()})
            return match.snapshot()


match_manager = MatchManager()
