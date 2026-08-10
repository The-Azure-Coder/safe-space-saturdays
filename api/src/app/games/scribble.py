"""Server-authoritative drawing and guessing game."""

from __future__ import annotations

import math
import random
import re
import time
from typing import Any

from app.games.connect_four import IllegalMove

WORDS = (
    # Nature and animals
    "rainbow", "sunflower", "cactus", "cloud", "volcano", "campfire",
    "mountain", "waterfall", "island", "palm tree", "snowflake", "moon",
    "star", "planet", "sun", "flower", "tree", "leaf", "mushroom",
    "butterfly", "dinosaur", "turtle", "penguin", "elephant", "giraffe",
    "lion", "monkey", "octopus", "whale", "shark", "dolphin", "rabbit",
    "cat", "dog", "frog", "snail", "bee", "spider", "parrot", "owl",
    # Places and transport
    "treehouse", "castle", "lighthouse", "school", "hospital", "library",
    "restaurant", "supermarket", "playground", "beach", "farm", "island",
    "rocket", "bicycle", "skateboard", "roller skates", "train", "bus",
    "airplane", "helicopter", "sailboat", "submarine", "canoe", "car",
    "motorcycle", "hot air balloon", "spaceship", "traffic light",
    # Food and everyday objects
    "pancake", "popcorn", "pizza", "hamburger", "ice cream", "cupcake",
    "cake", "sandwich", "taco", "watermelon", "banana", "apple", "cookie",
    "lollipop", "coconut", "teapot", "backpack", "umbrella", "sunglasses",
    "toothbrush", "alarm clock", "telephone", "camera", "television", "book",
    "pencil", "scissors", "key", "crown", "treasure chest", "present",
    # Activities, people, and playful ideas
    "guitar", "drum", "piano", "microphone", "ballerina", "superhero",
    "pirate", "wizard", "astronaut", "robot", "detective", "firefighter",
    "doctor", "chef", "gardener", "sailor", "dancing", "singing", "reading",
    "sleeping", "swimming", "fishing", "painting", "camping", "gardening",
    "football", "basketball", "tennis", "baseball", "kite", "yo-yo", "puzzle",
    "birthday party", "snowman", "mermaid", "dragon", "unicorn", "magic wand",
)

GUESS_SECONDS = 30


def _players(player_count: int, bot_players: tuple[int, ...]) -> list[dict[str, Any]]:
    names = ("You", "Milo Bot", "Maya Bot", "Sunny Bot")
    return [{"name": names[index], "is_bot": index in bot_players} for index in range(max(2, min(4, player_count)))]


def _hint(word: str) -> str:
    return " ".join("_" if char != " " else "/" for char in word)


def progressive_hint(word: str, deadline: float | None, now: float | None = None) -> str:
    """Reveal letters gradually during the guessing window without exposing the word."""
    if not word:
        return ""
    if deadline is None:
        return _hint(word)
    remaining = max(0.0, float(deadline) - (now if now is not None else time.time()))
    reveal_count = len([char for char in word if char != " "]) if remaining <= 0 else int(((GUESS_SECONDS - remaining) / GUESS_SECONDS) * len([char for char in word if char != " "]))
    revealed = 0
    output = []
    for char in word:
        if char == " ":
            output.append("/")
        elif revealed < reveal_count:
            output.append(char.upper())
            revealed += 1
        else:
            output.append("_")
    return " ".join(output)


def _word_choices(rng: random.Random, answer: str | None = None) -> list[str]:
    choices = rng.sample(list(WORDS), 3)
    if answer and answer not in choices:
        choices[0] = answer
    return choices


def new_scribble_state(rng: random.Random, player_count: int = 2, bot_players: tuple[int, ...] = (1,)) -> dict[str, Any]:
    players = _players(player_count, bot_players)
    choices = _word_choices(rng)
    return {
        "game": "scribble", "phase": "choosing", "round": 1, "rounds": 6,
        "current_player": 0, "current_drawer": 0, "player_count": len(players),
        "players": players, "word": choices[0], "word_choices": choices, "hint": _hint(choices[0]), "strokes": [],
        "guesses": [], "scores": [0 for _ in players], "winner": None, "draw": False,
        "round_winner": None, "round_points": [0 for _ in players], "next_drawer": 0,
        "guess_deadline": None, "bot_draw_pending": players[0].get("is_bot", False), "action_count": 0,
        "live_stroke": None,
        "last_event": "Choose a word, then sketch a clue for the other players!",
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
    state.setdefault("round_points", [0 for _ in range(count)])
    state.setdefault("word_choices", [state.get("word", "rainbow")])
    state.setdefault("next_drawer", state.get("current_drawer", 0))
    state.setdefault("guess_deadline", None)
    state.setdefault("live_stroke", None)
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
    if state.get("phase") == "choosing":
        return {"action": "choose_word", "word": state.get("word_choices", [WORDS[0]])[0]}
    return {"action": "bot_draw"}


def _levenshtein(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def _warm_guess(guess: str, answer: str) -> bool:
    if not guess or not answer:
        return False
    distance = _levenshtein(guess, answer)
    return distance <= max(1, round(len(answer) * 0.35))


def _begin_next_round(state: dict[str, Any]) -> None:
    next_drawer = int(state.get("next_drawer", state.get("current_drawer", 0)))
    choices = _word_choices(random, None)
    state["current_player"] = next_drawer
    state["current_drawer"] = next_drawer
    state["next_drawer"] = next_drawer
    state["word_choices"] = choices
    state["word"] = choices[0]
    state["hint"] = _hint(choices[0])
    state["strokes"] = []
    state["live_stroke"] = None
    state["guesses"] = []
    state["phase"] = "choosing"
    state["guess_deadline"] = None
    state["bot_draw_pending"] = bool(state["players"][next_drawer].get("is_bot"))
    state["last_event"] = f"{state['players'][next_drawer]['name']} is choosing a word."


def apply_scribble_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    normalise_scribble_state(state)
    if state["winner"] is not None or state.get("draw"):
        raise IllegalMove("The game is already finished")
    if not 0 <= player < int(state["player_count"]):
        raise IllegalMove("You are not a player in this game")
    drawer = int(state["current_drawer"])
    kind = action.get("action")
    if kind == "choose_word":
        if player != drawer or state.get("phase") != "choosing":
            raise IllegalMove("Only the current drawer can choose a word")
        word = str(action.get("word", "")).strip()
        choices = state.get("word_choices", [])
        if word not in choices:
            raise IllegalMove("Choose one of the offered words")
        state["word"] = word
        state["hint"] = _hint(word)
        state["phase"] = "drawing"
        state["bot_draw_pending"] = bool(state["players"][drawer].get("is_bot"))
        state["last_event"] = f"{state['players'][drawer]['name']} is drawing. Guess the word!"
    elif kind == "bot_draw":
        if player != drawer or not state.get("bot_draw_pending"):
            raise IllegalMove("The bot is not drawing right now")
        state["strokes"], state["phase"], state["bot_draw_pending"] = _bot_strokes(state["word"]), "guessing", False
        state["guess_deadline"] = time.time() + GUESS_SECONDS
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
        state["strokes"].append({"points": clean_points, "color": str(action.get("color", "#315542"))[:20], "size": max(2, min(24, int(action.get("size", 5)))), "erase": bool(action.get("erase", False))})
        state["live_stroke"] = None
        state["action_count"] += 1
        return state
    elif kind == "stroke_preview":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can preview a stroke")
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
        state["live_stroke"] = {"points": clean_points, "color": str(action.get("color", "#315542"))[:20], "size": max(2, min(24, int(action.get("size", 5)))), "erase": bool(action.get("erase", False))}
        return state
    elif kind == "stroke_segment":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can draw")
        points = action.get("points")
        if not isinstance(points, list) or len(points) != 2:
            raise IllegalMove("A line segment needs two points")
        clean_points = []
        for point in points:
            if not isinstance(point, dict):
                raise IllegalMove("Invalid drawing point")
            x, y = float(point.get("x", -1)), float(point.get("y", -1))
            if not 0 <= x <= 1 or not 0 <= y <= 1:
                raise IllegalMove("Drawing points must stay inside the canvas")
            clean_points.append({"x": round(x, 4), "y": round(y, 4)})
        if len(state["strokes"]) >= 600:
            raise IllegalMove("This sketch is full")
        state["strokes"].append({"points": clean_points, "color": str(action.get("color", "#315542"))[:20], "size": max(2, min(24, int(action.get("size", 5)))), "erase": bool(action.get("erase", False))})
        state["live_stroke"] = None
        state["action_count"] += 1
        return state
    elif kind == "clear":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can clear the canvas")
        state["strokes"] = []
        state["live_stroke"] = None
        state["action_count"] += 1
    elif kind == "end_turn":
        if player != drawer or state["phase"] != "drawing":
            raise IllegalMove("Only the current drawer can end the drawing turn")
        state["phase"], state["last_event"] = "guessing", "The drawing is ready. Take your best guess!"
        state["guess_deadline"] = time.time() + GUESS_SECONDS
    elif kind == "timeout":
        if state["phase"] != "guessing" or player == drawer:
            raise IllegalMove("The guessing round is not ready to end")
        state["phase"] = "round_result"
        state["round_winner"] = None
        state["round_points"] = [0 for _ in state["players"]]
        state["next_drawer"] = (drawer + 1) % int(state["player_count"])
        state["guess_deadline"] = None
        state["last_event"] = "Time is up — nobody found the word."
    elif kind == "continue":
        if state["phase"] != "round_result":
            raise IllegalMove("Finish the current drawing round first")
        state["round"] += 1
        _begin_next_round(state)
    elif kind == "hint_tick":
        if player == drawer or state["phase"] != "guessing":
            raise IllegalMove("Hints are only available during guessing")
        return state
    elif kind == "guess":
        if player == drawer or state["phase"] not in {"drawing", "guessing"}:
            raise IllegalMove("Drawers cannot guess their own clue")
        text = str(action.get("text", "")).strip()[:80]
        if not text:
            raise IllegalMove("Enter a guess first")
        if state.get("guess_deadline") and time.time() > float(state["guess_deadline"]):
            raise IllegalMove("The guessing time has ended")
        clean_text, clean_word = _clean_guess(text), _clean_guess(state["word"])
        correct = clean_text == clean_word
        warm = not correct and _warm_guess(clean_text, clean_word)
        state["guesses"].append({"player": player, "text": text, "correct": correct, "warm": warm})
        state["action_count"] += 1
        if not correct:
            state["last_event"] = f"Warm guess from {state['players'][player]['name']} — you are close!" if warm else f"{state['players'][player]['name']} made a guess. Keep drawing!"
            return state
        state["scores"][player] += 100
        state["scores"][drawer] += 50
        state["round_points"] = [0 for _ in state["players"]]
        state["round_points"][player] += 100
        state["round_points"][drawer] += 50
        state["round_winner"] = player
        if int(state["round"]) >= int(state["rounds"]):
            best = max(state["scores"])
            winners = [index for index, score in enumerate(state["scores"]) if score == best]
            state["winner"], state["draw"], state["phase"] = (winners[0] if len(winners) == 1 else None), len(winners) != 1, "finished"
            state["last_event"] = "All six rounds are complete!" if not state["draw"] else "All six rounds ended in a tie."
            return state
        next_drawer = (drawer + 1) % int(state["player_count"])
        state["next_drawer"] = next_drawer
        state["phase"] = "round_result"
        state["guess_deadline"] = None
        state["last_event"] = f"{state['players'][player]['name']} guessed correctly!"
    else:
        raise IllegalMove("Unknown drawing action")
    state["action_count"] += 1
    return state
