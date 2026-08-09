"""Server-authoritative drawing and guessing game."""

from __future__ import annotations

import math
import random
import re
from typing import Any

from app.games.connect_four import IllegalMove

WORDS = (
    "rainbow", "dinosaur", "rocket", "cactus", "guitar", "sunflower",
    "pancake", "volcano", "bicycle", "treehouse", "turtle", "popcorn",
    "butterfly", "campfire", "ice cream", "mermaid", "cloud", "sneaker",
)


def _players(player_count: int, bot_players: tuple[int, ...]) -> list[dict[str, Any]]:
    names = ("You", "Milo Bot", "Maya Bot", "Sunny Bot")
    return [{"name": names[index], "is_bot": index in bot_players} for index in range(max(2, min(4, player_count)))]


def _hint(word: str) -> str:
    return " ".join("_" if char != " " else "/" for char in word)


def new_scribble_state(rng: random.Random, player_count: int = 2, bot_players: tuple[int, ...] = (1,)) -> dict[str, Any]:
    players = _players(player_count, bot_players)
    word = rng.choice(WORDS)
    return {
        "game": "scribble", "phase": "drawing", "round": 1, "rounds": 6,
        "current_player": 0, "current_drawer": 0, "player_count": len(players),
        "players": players, "word": word, "hint": _hint(word), "strokes": [],
        "guesses": [], "scores": [0 for _ in players], "winner": None, "draw": False,
        "round_winner": None, "bot_draw_pending": False, "action_count": 0,
        "last_event": "Your turn to draw. Sketch a clue for the other players!",
    }


def normalise_scribble_state(state: dict[str, Any]) -> None:
    count = max(2, min(4, int(state.get("player_count", 2))))
    state.setdefault("round", 1)
    state.setdefault("rounds", 6)
    state.setdefault("current_player", 0)
    state.setdefault("current_drawer", state["current_player"])
    state.setdefault("phase", "drawing")
    state.setdefault("strokes", [])
    state.setdefault("guesses", [])
    state.setdefault("scores", [0 for _ in range(count)])
    state.setdefault("winner", None)
    state.setdefault("draw", False)
    state.setdefault("round_winner", None)
    state.setdefault("bot_draw_pending", False)
    state.setdefault("action_count", 0)
    state.setdefault("last_event", "Draw a clue for the other players!")


def _clean_guess(value: Any) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(value).casefold()).strip()


def _bot_strokes(word: str) -> list[dict[str, Any]]:
    seed = sum(ord(char) for char in word)
    cx, cy = 0.5 + ((seed % 7) - 3) / 40, 0.5 + ((seed % 5) - 2) / 40
    radius = 0.18 + (seed % 4) / 100
    circle = [{"x": round(cx + radius * math.cos(index * 0.4), 4), "y": round(cy + radius * math.sin(index * 0.4), 4)} for index in range(17)]
    line = [{"x": 0.22, "y": 0.72}, {"x": 0.5, "y": 0.28}, {"x": 0.78, "y": 0.72}]
    return [{"points": circle, "color": "#315542", "size": 6}, {"points": line, "color": "#d87958", "size": 5}]


def bot_draw_action(state: dict[str, Any]) -> dict[str, Any]:
    return {"action": "bot_draw"}


def apply_scribble_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    normalise_scribble_state(state)
    if state["winner"] is not None or state.get("draw"):
        raise IllegalMove("The game is already finished")
    if not 0 <= player < int(state["player_count"]):
        raise IllegalMove("You are not a player in this game")
    drawer = int(state["current_drawer"])
    kind = action.get("action")
    if kind == "bot_draw":
        if player != drawer or not state.get("bot_draw_pending"):
            raise IllegalMove("The bot is not drawing right now")
        state["strokes"], state["phase"], state["bot_draw_pending"] = _bot_strokes(state["word"]), "guessing", False
        state["last_event"] = f"{state['players'][drawer]['name']} finished drawing. What is it?"
    elif kind == "stroke":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can draw")
        points = action.get("points")
        if not isinstance(points, list) or not 2 <= len(points) <= 120:
            raise IllegalMove("A stroke needs between 2 and 120 points")
        clean_points = []
        for point in points:
            if not isinstance(point, dict):
                raise IllegalMove("Invalid drawing point")
            x, y = float(point.get("x", -1)), float(point.get("y", -1))
            if not 0 <= x <= 1 or not 0 <= y <= 1:
                raise IllegalMove("Drawing points must stay inside the canvas")
            clean_points.append({"x": round(x, 4), "y": round(y, 4)})
        if len(state["strokes"]) >= 120:
            raise IllegalMove("This sketch is full")
        state["strokes"].append({"points": clean_points, "color": str(action.get("color", "#315542"))[:20], "size": max(2, min(18, int(action.get("size", 5))))})
        state["action_count"] += 1
        return state
    elif kind == "clear":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can clear the canvas")
        state["strokes"] = []
    elif kind == "end_turn":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can end the drawing turn")
        state["phase"], state["last_event"] = "guessing", "The drawing is ready. Take your best guess!"
    elif kind == "guess":
        if player == drawer or state["phase"] not in {"drawing", "guessing"}:
            raise IllegalMove("Drawers cannot guess their own clue")
        text = str(action.get("text", "")).strip()[:80]
        if not text:
            raise IllegalMove("Enter a guess first")
        correct = _clean_guess(text) == _clean_guess(state["word"])
        state["guesses"].append({"player": player, "text": text, "correct": correct})
        state["action_count"] += 1
        if not correct:
            state["last_event"] = f"{state['players'][player]['name']} made a guess. Keep drawing!"
            return state
        state["scores"][player] += 100
        state["scores"][drawer] += 50
        state["round_winner"] = player
        if int(state["round"]) >= int(state["rounds"]):
            best = max(state["scores"])
            winners = [index for index, score in enumerate(state["scores"]) if score == best]
            state["winner"], state["draw"], state["phase"] = (winners[0] if len(winners) == 1 else None), len(winners) != 1, "finished"
            state["last_event"] = "All six rounds are complete!" if not state["draw"] else "All six rounds ended in a tie."
            return state
        next_drawer = (drawer + 1) % int(state["player_count"])
        state["round"] += 1
        state["current_player"] = next_drawer
        state["current_drawer"] = next_drawer
        state["word"] = random.choice(WORDS)
        state["hint"] = _hint(state["word"])
        state["strokes"] = []
        state["guesses"] = []
        state["phase"] = "drawing"
        state["bot_draw_pending"] = bool(state["players"][next_drawer].get("is_bot"))
        state["last_event"] = f"{state['players'][player]['name']} guessed correctly! Round {state['round']} begins."
    else:
        raise IllegalMove("Unknown drawing action")
    state["action_count"] += 1
    return state
