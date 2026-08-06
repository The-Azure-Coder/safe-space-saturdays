import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.games.connect_four import IllegalMove
from app.games.multi import apply_action, bot_action, new_state


@dataclass
class UniversalMatch:
    id: str
    room_id: int
    game_type: str
    state: dict[str, Any]
    player_ids: dict[int, int]
    bot_player: int | None = 1
    sockets: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    reward_granted: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "match_id": self.id,
            "room_id": self.room_id,
            "game": self.game_type,
            "state": self.state,
        }


class UniversalMatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, UniversalMatch] = {}

    def create(self, room_id: int, user_id: int, game_type: str) -> UniversalMatch:
        match = UniversalMatch(
            id=str(uuid4()),
            room_id=room_id,
            game_type=game_type,
            state=new_state(game_type),
            player_ids={user_id: 0},
        )
        self.matches[match.id] = match
        return match

    def get(self, match_id: str) -> UniversalMatch | None:
        return self.matches.get(match_id)

    async def broadcast(self, match: UniversalMatch) -> None:
        for socket in list(match.sockets):
            try:
                await socket.send_json({"type": "state", "match": match.snapshot()})
            except Exception:
                match.sockets.discard(socket)

    async def action(
        self, match: UniversalMatch, user_id: int, payload: dict[str, Any]
    ) -> UniversalMatch:
        async with match.lock:
            player = match.player_ids.get(user_id)
            if player is None:
                raise IllegalMove("You are not a player in this match")
            match.state = apply_action(match.state, player, payload)
            await self.broadcast(match)
            if (
                match.bot_player is not None
                and match.state.get("winner") is None
                and match.state.get("current_player") == match.bot_player
            ):
                try:
                    match.state = apply_action(
                        match.state, match.bot_player, bot_action(match.state, match.bot_player)
                    )
                    await self.broadcast(match)
                except IllegalMove:
                    # A bot may not have a legal move; passing is the safe fallback for dominoes.
                    if match.game_type == "dominoes":
                        match.state = apply_action(match.state, match.bot_player, {"pass": True})
                        await self.broadcast(match)
            return match


universal_matches = UniversalMatchManager()
