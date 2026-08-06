"""Small, deterministic game engines used by the shared match transport.

The browser sends intentions only. Every random value, legal-move check, score, and
winner is decided here on the server.
"""

from __future__ import annotations

import random
from typing import Any

from app.games.connect_four import IllegalMove

GAME_TYPES = {"ludo", "dominoes", "bingo", "trivia"}
_RNG = random.Random()


def _turn(state: dict[str, Any], player: int) -> None:
    if state["winner"] is not None or state.get("draw", False):
        raise IllegalMove("The match is already finished")
    if state["current_player"] != player:
        raise IllegalMove("It is not your turn")


def new_state(game_type: str) -> dict[str, Any]:
    if game_type not in GAME_TYPES:
        raise IllegalMove("This game is not available yet")
    if game_type == "ludo":
        return {
            "game": "ludo", "current_player": 0, "winner": None,
            "positions": [[-1, -1, -1, -1] for _ in range(2)], "roll": None,
        }
    if game_type == "dominoes":
        deck = [[left, right] for left in range(7) for right in range(left, 7)]
        _RNG.shuffle(deck)
        return {
            "game": "dominoes", "current_player": 0, "winner": None, "draw": False,
            "hands": [deck[:7], deck[7:14]], "board": [], "passes": 0,
        }
    if game_type == "bingo":
        numbers = list(range(1, 76))
        _RNG.shuffle(numbers)
        card = [sorted(numbers[index * 5 : index * 5 + 5]) for index in range(5)]
        card[2][2] = 0
        return {
            "game": "bingo", "current_player": 0, "winner": None, "draw": False,
            "card": card,
            "marked": [[row == 2 and col == 2 for col in range(5)] for row in range(5)],
            "drawn": [], "remaining": list(range(1, 76)),
        }
    return {
        "game": "trivia", "current_player": 0, "winner": None, "draw": False,
        "question_index": 0, "scores": [0, 0], "answered": False,
        "question": "Which word best describes a gentle pause?",
        "options": ["Rush", "Rest", "Noise", "Pressure"], "correct": 1,
    }


def _next_player(state: dict[str, Any]) -> None:
    state["current_player"] = 1 - state["current_player"]


def _bingo_complete(marked: list[list[bool]]) -> bool:
    lines = marked + [[marked[row][col] for row in range(5)] for col in range(5)]
    lines.extend(
        [
            [marked[index][index] for index in range(5)],
            [marked[index][4 - index] for index in range(5)],
        ]
    )
    return any(all(line) for line in lines)


def apply_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    game = state["game"]
    if game == "ludo":
        _turn(state, player)
        token = action.get("token")
        if not isinstance(token, int) or not 0 <= token < 4:
            raise IllegalMove("Choose one of your four tokens")
        roll = _RNG.randint(1, 6)
        position = state["positions"][player][token]
        if position == -1 and roll != 6:
            raise IllegalMove("A token needs a six to leave base")
        new_position = 0 if position == -1 else position + roll
        if new_position > 56:
            raise IllegalMove("That token needs an exact roll to reach home")
        state["positions"][player][token] = new_position
        state["roll"] = roll
        if all(value == 56 for value in state["positions"][player]):
            state["winner"] = player
        elif roll != 6:
            _next_player(state)
        return state
    if game == "dominoes":
        _turn(state, player)
        if action.get("pass") is True:
            state["passes"] += 1
            if state["passes"] >= 2:
                totals = [sum(sum(tile) for tile in hand) for hand in state["hands"]]
                state["winner"] = 0 if totals[0] <= totals[1] else 1
            else:
                _next_player(state)
            return state
        index = action.get("tile_index")
        side = action.get("side", "right")
        if not isinstance(index, int) or not 0 <= index < len(state["hands"][player]):
            raise IllegalMove("Choose a tile from your hand")
        tile = state["hands"][player][index]
        if state["board"]:
            edge = state["board"][0][0] if side == "left" else state["board"][-1][1]
            if edge not in tile:
                raise IllegalMove("That tile does not match the board")
        state["hands"][player].pop(index)
        if side == "left":
            state["board"].insert(0, tile)
        else:
            state["board"].append(tile)
        state["passes"] = 0
        if not state["hands"][player]:
            state["winner"] = player
        else:
            _next_player(state)
        return state
    if game == "bingo":
        _turn(state, player)
        if action.get("action") == "draw":
            if not state["remaining"]:
                state["draw"] = True
                return state
            number = state["remaining"].pop()
            state["drawn"].append(number)
            for row in range(5):
                for col in range(5):
                    if state["card"][row][col] == number:
                        state["marked"][row][col] = True
            return state
        if action.get("action") == "claim" and _bingo_complete(state["marked"]):
            state["winner"] = player
            return state
        raise IllegalMove("Draw a ball before claiming bingo")
    _turn(state, player)
    answer = action.get("answer")
    if not isinstance(answer, int) or not 0 <= answer < 4:
        raise IllegalMove("Choose one answer")
    if state["answered"]:
        raise IllegalMove("This question is already answered")
    if answer == state["correct"]:
        state["scores"][player] += 100
    state["answered"] = True
    if state["question_index"] >= 4:
        state["winner"] = 0 if state["scores"][0] >= state["scores"][1] else 1
    else:
        state["question_index"] += 1
        state["answered"] = False
        _next_player(state)
    return state


def bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    game = state["game"]
    if game == "ludo":
        return {"token": 0}
    if game == "dominoes":
        for index, tile in enumerate(state["hands"][player]):
            right_edge = state["board"][-1][1] if state["board"] else None
            left_edge = state["board"][0][0] if state["board"] else None
            if not state["board"] or tile[0] in (right_edge, left_edge) or tile[1] in (
                right_edge,
                left_edge,
            ):
                return {"tile_index": index, "side": "right"}
        return {"pass": True}
    if game == "bingo":
        return {"action": "draw"}
    return {"answer": state["correct"] if _RNG.random() > 0.35 else _RNG.randrange(4)}
