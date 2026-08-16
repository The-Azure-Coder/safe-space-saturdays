"""Server-authoritative ABC Fast or Slow rounds.

The browser only sends answers and votes. The server owns the timer deadline,
validation, duplicate detection, scoring, round progression, and winner.
"""
from __future__ import annotations

import random
import time
from typing import Any

from app.games.connect_four import IllegalMove

CATEGORIES = ("Animal", "Place", "Food", "Thing")
BOT_WORDS = {
    "Animal": ("ant", "bear", "cat", "dog", "eagle", "fox", "goat", "horse", "otter", "zebra"),
    "Place": ("berlin", "cairo", "dublin", "jamaica", "london", "miami", "paris", "rome", "sydney", "tokyo"),
    "Food": ("apple", "bread", "curry", "donut", "eggs", "fig", "grapes", "honey", "rice", "taco"),
    "Thing": ("anchor", "book", "chair", "drum", "envelope", "fork", "guitar", "hat", "lamp", "phone"),
}
ROUND_SECONDS = 45


def new_abc_state(rng: random.Random, player_count: int, bot_players: tuple[int, ...]) -> dict[str, Any]:
    count = max(2, min(6, player_count))
    players = [{"name": "You" if i == 0 else f"Player {i + 1}", "is_bot": i in bot_players} for i in range(count)]
    return _round(rng, players, [0] * count, 1)


def _round(rng: random.Random, players: list[dict[str, Any]], scores: list[int], round_number: int) -> dict[str, Any]:
    letter = rng.choice("ABCDEFGHLMPRST")
    return {
        "game": "abc-fast-slow", "players": players, "player_count": len(players), "current_player": 0,
        "winner": None, "draw": False, "phase": "answering", "round": round_number, "rounds": 3,
        "letter": letter, "categories": list(CATEGORIES), "answers": [{} for _ in players],
        "scores": scores, "submitted": [False for _ in players], "votes": [{} for _ in players],
        "voted": [False for _ in players], "deadline": time.time() + ROUND_SECONDS,
        "last_event": f"Round {round_number}: answers begin with {letter}.",
    }


def _submit(state: dict[str, Any], player: int, action: dict[str, Any]) -> None:
    if state["submitted"][player]:
        raise IllegalMove("You already submitted this round")
    raw = action.get("answers", {})
    if not isinstance(raw, dict):
        raw = {}
    state["answers"][player] = {
        category: str(raw.get(category, "")).strip()[:40] for category in CATEGORIES
    }
    state["submitted"][player] = True
    if all(state["submitted"]):
        state["phase"] = "voting"
        state["deadline"] = None
        state["last_event"] = "Answers are in. Vote valid or invalid for each answer."


def _vote(state: dict[str, Any], player: int, action: dict[str, Any]) -> None:
    if state["voted"][player]:
        raise IllegalMove("You already voted this round")
    target = action.get("target")
    category = action.get("category")
    if not isinstance(target, int) or not 0 <= target < state["player_count"]:
        raise IllegalMove("Choose a player answer to review")
    if category not in CATEGORIES:
        raise IllegalMove("Choose a valid category")
    state["votes"][player][f"{target}:{category}"] = bool(action.get("valid", False))
    # A single vote action represents the reviewer's complete ballot. This keeps
    # the game quick while still making every player participate in validation.
    if len(state["votes"][player]) == state["player_count"] * len(CATEGORIES):
        state["voted"][player] = True
    if all(state["voted"]):
        _score_round(state)


def apply_abc_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    if not 0 <= player < state["player_count"]:
        raise IllegalMove("You are not a player in this game")
    kind = action.get("action", "submit")
    if kind == "play_again":
        if state.get("winner") is None and not state.get("draw"):
            raise IllegalMove("Finish the game before playing again")
        return _round(random.Random(), state["players"], list(state["scores"]), 1)
    if state.get("phase") == "answering":
        if kind not in {"submit", "timeout"}:
            raise IllegalMove("Submit your answers before voting")
        expired = state.get("deadline") is not None and time.time() >= float(state["deadline"])
        if kind == "timeout" and not expired:
            raise IllegalMove("The round timer has not expired")
        if expired:
            kind = "timeout"
        _submit(state, player, {} if kind == "timeout" else action)
        return state
    if state.get("phase") == "voting":
        if kind != "vote":
            raise IllegalMove("Review the answers before continuing")
        _vote(state, player, action)
        return state
    raise IllegalMove("This round is already complete")


def _score_round(state: dict[str, Any]) -> None:
    letter = state["letter"].lower()
    accepted: dict[str, list[int]] = {category: [] for category in CATEGORIES}
    for target, answers in enumerate(state["answers"]):
        for category in CATEGORIES:
            value = answers.get(category, "").lower()
            key = f"{target}:{category}"
            approvals = sum(bool(ballot.get(key)) for ballot in state["votes"])
            if value and value.startswith(letter) and approvals > state["player_count"] // 2:
                accepted[category].append(target)
    for category, targets in accepted.items():
        values = {target: state["answers"][target].get(category, "").lower() for target in targets}
        for target, value in values.items():
            if list(values.values()).count(value) == 1:
                state["scores"][target] += 10
    if state["round"] >= state["rounds"]:
        best = max(state["scores"])
        winners = [i for i, score in enumerate(state["scores"]) if score == best]
        state["winner"] = winners[0] if len(winners) == 1 else None
        state["draw"] = len(winners) > 1
        state["phase"] = "complete"
        state["last_event"] = "Game complete. Unique valid answers score 10 points."
    else:
        state["phase"] = "round_result"
        state["last_event"] = "Round complete. Unique valid answers score 10 points."


def next_abc_round(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("phase") != "round_result":
        raise IllegalMove("The round is not ready to continue")
    next_state = _round(random.Random(), state["players"], list(state["scores"]), state["round"] + 1)
    state.clear()
    state.update(next_state)
    return state


def abc_bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    if state.get("phase") == "answering":
        letter = state["letter"].lower()
        answers = {
            category: next((word for word in BOT_WORDS[category] if word.startswith(letter)), "")
            for category in CATEGORIES
        }
        return {"action": "submit", "answers": answers}
    if state.get("phase") == "voting":
        # Bot accepts non-empty answers starting with the letter and rejects the rest.
        target, category = next(
            (candidate_target, candidate_category)
            for candidate_target in range(state["player_count"])
            for candidate_category in CATEGORIES
            if f"{candidate_target}:{candidate_category}" not in state["votes"][player]
        )
        value = state["answers"][target].get(category, "").lower()
        return {"action": "vote", "target": target, "category": category, "valid": bool(value and value.startswith(state["letter"].lower()))}
    raise IllegalMove("The bot has no ABC action right now")
