import asyncio
from copy import deepcopy
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
    bot_players: tuple[int, ...] = ()
    sockets: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    reward_granted: bool = False

    def snapshot(self) -> dict[str, Any]:
        public_state = deepcopy(self.state)
        if self.game_type == "dominoes":
            hands = public_state.get("hands", [])
            public_state["hand_counts"] = [len(hand) for hand in hands]
            public_state["hands"] = [hands[0] if hands else []] + [
                [] for _ in hands[1:]
            ]
        if self.game_type == "trivia":
            correct = public_state.pop("correct", None)
            if public_state.get("phase") in {"reveal", "complete"}:
                public_state["correct_answer"] = correct
        return {
            "match_id": self.id,
            "room_id": self.room_id,
            "game": self.game_type,
            "state": public_state,
        }


class UniversalMatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, UniversalMatch] = {}

    def create(
        self, room_id: int, user_id: int, game_type: str, player_count: int = 2
    ) -> UniversalMatch:
        effective_count = player_count if game_type in {"ludo", "dominoes"} else 2
        match = UniversalMatch(
            id=str(uuid4()),
            room_id=room_id,
            game_type=game_type,
            state=new_state(game_type, effective_count),
            player_ids={user_id: 0},
            bot_players=tuple(range(1, effective_count)),
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
            bot_player = match.bot_player
            bot_players = match.bot_players or ((bot_player,) if bot_player is not None else ())
            bot_turn = (
                bool(bot_players)
                and match.state.get("winner") is None
                and match.state.get("current_player") in bot_players
            )
            if bot_turn and match.game_type == "ludo":
                # Continue across every bot seat until play returns to the human.
                for _ in range(96):
                    current_bot = int(match.state.get("current_player", 0))
                    if (
                        match.state.get("winner") is not None
                        or current_bot not in bot_players
                    ):
                        break
                    # Give connected players enough time to see the bot think,
                    # roll, and choose a token instead of receiving every state
                    # in a single imperceptible burst.
                    if match.sockets:
                        await asyncio.sleep(
                            0.45 if match.state.get("phase") == "roll" else 0.65
                        )
                    match.state = apply_action(
                        match.state,
                        current_bot,
                        bot_action(match.state, current_bot),
                    )
                    await self.broadcast(match)
                else:
                    raise IllegalMove("The bot turn could not be completed")
            elif bot_turn:
                for _ in range(12):
                    current_bot = int(match.state.get("current_player", 0))
                    if (
                        match.state.get("winner") is not None
                        or match.state.get("draw", False)
                        or current_bot not in bot_players
                    ):
                        break
                    if match.sockets:
                        await asyncio.sleep(0.7)
                    match.state = apply_action(
                        match.state,
                        current_bot,
                        bot_action(match.state, current_bot),
                    )
                    await self.broadcast(match)
                else:
                    raise IllegalMove("The bot turns could not be completed")
            return match


universal_matches = UniversalMatchManager()
