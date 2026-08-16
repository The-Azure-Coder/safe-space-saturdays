"""Server-authoritative ABC Fast or Slow rounds."""
from __future__ import annotations

import random
from typing import Any

from app.games.connect_four import IllegalMove

CATEGORIES = ("Animal", "Place", "Food", "Thing")
WORDS = {
    "Animal": ("ant", "bear", "cat", "dog", "eagle", "fox", "goat", "horse", "otter", "zebra"),
    "Place": ("berlin", "cairo", "dublin", "jamaica", "london", "miami", "paris", "rome", "sydney", "tokyo"),
    "Food": ("apple", "bread", "curry", "donut", "eggs", "fig", "grapes", "honey", "rice", "taco"),
    "Thing": ("anchor", "book", "chair", "drum", "envelope", "fork", "guitar", "hat", "lamp", "phone"),
}


def new_abc_state(rng: random.Random, player_count: int, bot_players: tuple[int, ...]) -> dict[str, Any]:
    count = max(2, min(6, player_count))
    players = [{"name": "You" if i == 0 else f"Player {i + 1}", "is_bot": i in bot_players} for i in range(count)]
    return _round(rng, players, [0] * count, 1)


def _round(rng: random.Random, players: list[dict[str, Any]], scores: list[int], round_number: int) -> dict[str, Any]:
    # Keep rounds playable for bots while still giving humans a varied letter.
    letter = rng.choice("ABCDEFGHLMPRST")
    return {"game": "abc-fast-slow", "players": players, "player_count": len(players), "current_player": 0,
            "winner": None, "draw": False, "phase": "answering", "round": round_number, "rounds": 3,
            "letter": letter, "categories": list(CATEGORIES), "answers": [{} for _ in players],
            "scores": scores, "submitted": [False for _ in players], "deadline": None,
            "last_event": f"Round {round_number}: answers begin with {letter}."}


def apply_abc_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    if not 0 <= player < state["player_count"]:
        raise IllegalMove("You are not a player in this game")
    kind = action.get("action", "submit")
    if kind == "play_again":
        if state.get("winner") is None:
            raise IllegalMove("Finish the game before playing again")
        players = state["players"]
        return _round(random.Random(), players, list(state["scores"]), 1)
    if state.get("phase") != "answering":
        raise IllegalMove("This round is already complete")
    if state["submitted"][player]:
        raise IllegalMove("You already submitted this round")
    raw = action.get("answers", {})
    answers = {category: str(raw.get(category, "")).strip()[:40] for category in CATEGORIES}
    state["answers"][player] = answers
    state["submitted"][player] = True
    if all(state["submitted"]):
        _score_round(state)
    return state


def _score_round(state: dict[str, Any]) -> None:
    letter = state["letter"].lower()
    for category in CATEGORIES:
        counts: dict[str, int] = {}
        for answers in state["answers"]:
            value = answers.get(category, "").lower()
            if value.startswith(letter) and value:
                counts[value] = counts.get(value, 0) + 1
        for player, answers in enumerate(state["answers"]):
            value = answers.get(category, "").lower()
            if value.startswith(letter) and value and counts.get(value) == 1:
                state["scores"][player] += 10
    if state["round"] >= state["rounds"]:
        best = max(state["scores"])
        winners = [i for i, score in enumerate(state["scores"]) if score == best]
        state["winner"] = winners[0] if len(winners) == 1 else None
        state["draw"] = len(winners) > 1
        state["phase"] = "complete"
        state["last_event"] = "Game complete. Unique answers score 10 points."
    else:
        state["phase"] = "round_result"
        state["last_event"] = "Round complete. Unique valid answers score 10 points."


def next_abc_round(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("phase") != "round_result":
        raise IllegalMove("The round is not ready to continue")
    next_state = _round(random.Random(), state["players"], list(state["scores"]), state["round"] + 1)
    state.clear(); state.update(next_state)
    return state


def abc_bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    letter = state["letter"].lower()
    answers = {category: next((word for word in WORDS[category] if word.startswith(letter)), "") for category in CATEGORIES}
    return {"action": "submit", "answers": answers}
