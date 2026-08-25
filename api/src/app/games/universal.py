import asyncio
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.games.connect_four import IllegalMove
from app.games.multi import apply_action, bot_action, new_state
from app.games.scribble import progressive_hint
from app.games.together import together_public_event

logger = logging.getLogger("safe_space_saturdays.games.websocket")


@dataclass
class UniversalMatch:
    id: str
    room_id: int
    game_type: str
    state: dict[str, Any]
    player_ids: dict[int, int]
    bot_player: int | None = 1
    bot_players: tuple[int, ...] = ()
    sockets: dict[WebSocket, int] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    settlement_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    reward_granted: bool = False
    version: int = 0
    timer_task: asyncio.Task[None] | None = None

    def spectator_count(self) -> int:
        return sum(user_id not in self.player_ids for user_id in self.sockets.values())

    def snapshot(
        self,
        user_id: int | None = None,
        spectator: bool = False,
        spectator_count: int | None = None,
    ) -> dict[str, Any]:
        public_state = deepcopy(self.state)
        is_spectator = spectator or (user_id is not None and user_id not in self.player_ids)
        seat = -1 if spectator else self.player_ids.get(user_id, -1) if user_id is not None else 0
        public_state["seat_index"] = seat
        if self.game_type == "dominoes":
            hands = public_state.get("hands", [])
            public_state["hand_counts"] = [len(hand) for hand in hands]
            public_state["hands"] = (
                [[] for _ in hands]
                if is_spectator
                else [hands[seat] if index == seat else [] for index in range(len(hands))]
            )
        if self.game_type == "bingo":
            cards = public_state.pop("cards", [])
            marked_cards = public_state.pop("marked_cards", [])
            public_state["card"] = [] if is_spectator or seat < 0 else cards[seat]
            public_state["marked"] = [] if is_spectator or seat < 0 else marked_cards[seat]
        if self.game_type == "trivia":
            public_state.pop("clues", None)
            correct = public_state.pop("correct", None)
            if public_state.get("phase") in {"reveal", "complete"}:
                public_state["correct_answer"] = correct
            selected = public_state.get("selected_answers", [])
            public_state["selected_answers"] = [
                answer
                if not is_spectator
                and (index == seat or public_state.get("phase") in {"reveal", "complete"})
                else None
                for index, answer in enumerate(selected)
            ]
        if self.game_type == "scribble":
            drawer = int(public_state.get("current_drawer", 0))
            if seat != drawer:
                public_state.pop("word", None)
                public_state.pop("word_choices", None)
                if public_state.get("phase") in {"guessing", "round_result", "finished"}:
                    public_state["hint"] = public_state.get("word") or progressive_hint(
                        self.state.get("word", ""), self.state.get("guess_deadline")
                    )
                    if public_state.get("phase") in {"round_result", "finished"}:
                        public_state["hint"] = str(self.state.get("word", "")).upper()
            public_state["is_drawer"] = not is_spectator and seat == drawer
            public_state["drawer_name"] = public_state.get("players", [{}])[drawer].get(
                "name", "The drawer"
            )
        return {
            "match_id": self.id,
            "room_id": self.room_id,
            "game": self.game_type,
            "state": public_state,
            "spectator": is_spectator,
            "spectator_count": self.spectator_count()
            if spectator_count is None
            else spectator_count,
        }


class UniversalMatchManager:
    def __init__(self) -> None:
        self.matches: dict[str, UniversalMatch] = {}

    def create(
        self,
        room_id: int,
        user_id: int,
        game_type: str,
        player_count: int = 2,
        player_ids: dict[int, int] | None = None,
        bot_players: tuple[int, ...] | None = None,
        player_names: dict[int, str] | None = None,
        bot_difficulty: str = "friendly",
    ) -> UniversalMatch:
        effective_count = (
            player_count
            if game_type in {"ludo", "dominoes", "scribble", "abc-fast-slow", "together"}
            else 2
        )
        resolved_bot_players = (
            ()
            if game_type == "together"
            else bot_players
            if bot_players is not None
            else tuple(range(1, effective_count))
        )
        state = new_state(game_type, effective_count, resolved_bot_players, bot_difficulty)
        state["bot_difficulty"] = bot_difficulty
        for seat, name in (player_names or {}).items():
            if seat < len(state.get("players", [])):
                state["players"][seat]["name"] = name
                state["players"][seat]["is_bot"] = seat in resolved_bot_players
        match = UniversalMatch(
            id=str(uuid4()),
            room_id=room_id,
            game_type=game_type,
            state=state,
            player_ids=player_ids or {user_id: 0},
            bot_player=resolved_bot_players[0] if resolved_bot_players else None,
            bot_players=resolved_bot_players,
        )
        self.matches[match.id] = match
        return match

    def get(self, match_id: str) -> UniversalMatch | None:
        return self.matches.get(match_id)

    async def broadcast(self, match: UniversalMatch) -> None:
        for socket, user_id in list(match.sockets.items()):
            try:
                await socket.send_json(
                    {
                        "type": "state",
                        "match": match.snapshot(user_id, spectator_count=match.spectator_count()),
                    }
                )
            except Exception:
                logger.warning(
                    "game_socket_send_failed match_id=%s user_id=%s",
                    match.id,
                    user_id,
                    exc_info=True,
                )
                match.sockets.pop(socket, None)

    async def broadcast_drawing_segment(
        self, match: UniversalMatch, segment: dict[str, Any]
    ) -> None:
        for socket in list(match.sockets):
            try:
                await socket.send_json({"type": "drawing_segment", "segment": segment})
            except Exception:
                logger.warning(
                    "game_drawing_socket_send_failed match_id=%s",
                    match.id,
                    exc_info=True,
                )
                match.sockets.pop(socket, None)

    async def action(
        self,
        match: UniversalMatch,
        user_id: int,
        payload: dict[str, Any],
        *,
        broadcast: bool = True,
    ) -> UniversalMatch:
        async with match.lock:
            return await self.action_locked(match, user_id, payload, broadcast=broadcast)

    async def action_locked(
        self,
        match: UniversalMatch,
        user_id: int,
        payload: dict[str, Any],
        *,
        broadcast: bool = True,
    ) -> UniversalMatch:
        player = match.player_ids.get(user_id)
        if player is None:
            raise IllegalMove("You are not a player in this match")
        match.state = apply_action(match.state, player, payload)
        if payload.get("action") == "play_again":
            match.reward_granted = False
        if match.game_type == "together":
            if broadcast:
                await self.broadcast_together(match)
            return match
        if match.game_type == "scribble" and payload.get("action") == "stroke_segment":
            if broadcast:
                await self.broadcast_drawing_segment(match, match.state["strokes"][-1])
        elif broadcast:
            await self.broadcast(match)
        bot_player = match.bot_player
        bot_players = match.bot_players or ((bot_player,) if bot_player is not None else ())
        if match.game_type == "abc-fast-slow":
            # ABC has simultaneous answer/review phases, so it does not use
            # current_player as a turn gate. Advance each bot's outstanding
            # submission or ballot at human-readable speed.
            for _ in range(160):
                if match.state.get("phase") not in {
                    "letter_picker",
                    "letter_picker_running",
                    "answering",
                    "voting",
                }:
                    break
                phase = match.state.get("phase")
                if phase == "letter_picker":
                    chooser = int(match.state.get("letter_chooser", -1))
                    pending = chooser if chooser in bot_players else None
                elif phase == "letter_picker_running":
                    chooser = int(match.state.get("letter_chooser", -1))
                    pending = chooser if chooser in bot_players else None
                elif phase == "answering":
                    pending = next(
                        (seat for seat in bot_players if not match.state["submitted"][seat]), None
                    )
                else:
                    pending = next(
                        (seat for seat in bot_players if not match.state["voted"][seat]), None
                    )
                if pending is None:
                    break
                if broadcast and match.sockets:
                    await asyncio.sleep(0.35)
                match.state = apply_action(
                    match.state, int(pending), bot_action(match.state, int(pending))
                )
                if broadcast:
                    await self.broadcast(match)
            return match
        bot_turn = (
            bool(bot_players)
            and match.state.get("winner") is None
            and match.state.get("current_player") in bot_players
            and (
                match.game_type != "scribble"
                or match.state.get("phase") == "choosing"
                or match.state.get("bot_draw_pending", False)
            )
        )
        if bot_turn and match.game_type == "ludo":
            # Continue across every bot seat until play returns to the human.
            human_moved = payload.get("action") == "move"
            for _ in range(96):
                current_bot = int(match.state.get("current_player", 0))
                if match.state.get("winner") is not None or current_bot not in bot_players:
                    break
                # Give connected players enough time to see the bot think,
                # roll, and choose a token instead of receiving every state
                # in a single imperceptible burst.
                if broadcast and match.sockets:
                    # Let the browser finish the human's square-by-square
                    # animation before the next player receives the die.
                    if human_moved:
                        await asyncio.sleep(2.05)
                        human_moved = False
                    else:
                        await asyncio.sleep(0.95 if match.state.get("phase") == "roll" else 1.15)
                match.state = apply_action(
                    match.state,
                    current_bot,
                    bot_action(match.state, current_bot),
                )
                if broadcast:
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
                if broadcast and match.sockets:
                    await asyncio.sleep(0.7)
                match.state = apply_action(
                    match.state,
                    current_bot,
                    bot_action(match.state, current_bot),
                )
                if broadcast:
                    await self.broadcast(match)
            else:
                raise IllegalMove("The bot turns could not be completed")
        return match

    async def broadcast_together(self, match: UniversalMatch) -> None:
        event = {"type": "together", "match_id": match.id, **together_public_event(match.state)}
        for socket in list(match.sockets):
            try:
                await socket.send_json(event)
            except Exception:
                logger.warning(
                    "game_together_socket_send_failed match_id=%s",
                    match.id,
                    exc_info=True,
                )
                match.sockets.pop(socket, None)


universal_matches = UniversalMatchManager()
