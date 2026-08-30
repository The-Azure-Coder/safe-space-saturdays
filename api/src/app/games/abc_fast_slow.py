"""Server-authoritative ABC Fast or Slow rounds.

The browser only sends answers and votes. The server owns the timer deadline,
validation, duplicate detection, scoring, round progression, and winner.
"""

from __future__ import annotations

import random
import time
from typing import Any

from app.games.connect_four import IllegalMove

DEFAULT_CATEGORIES = ("Animal", "Place", "Food", "Thing")
CATEGORIES = DEFAULT_CATEGORIES
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BOT_WORDS = {
    "Animal": ("ant", "bear", "cat", "dog", "eagle", "fox", "goat", "horse", "otter", "zebra"),
    "Place": (
        "berlin",
        "cairo",
        "dublin",
        "jamaica",
        "london",
        "miami",
        "paris",
        "rome",
        "sydney",
        "tokyo",
    ),
    "Food": ("apple", "bread", "curry", "donut", "eggs", "fig", "grapes", "honey", "rice", "taco"),
    "Thing": (
        "anchor",
        "book",
        "chair",
        "drum",
        "envelope",
        "fork",
        "guitar",
        "hat",
        "lamp",
        "phone",
    ),
}
ROUND_SECONDS = 45
PICKER_SECONDS = 15
PICK_INTERVALS = {"fast": 0.08, "slow": 0.28}


def new_abc_state(
    rng: random.Random, player_count: int, bot_players: tuple[int, ...],
    categories: list[str] | tuple[str, ...] | None = None,
    majority_invalid: bool = True,
) -> dict[str, Any]:
    count = max(2, player_count)
    players = [
        {"name": "You" if i == 0 else f"Player {i + 1}", "is_bot": i in bot_players}
        for i in range(count)
    ]
    return _round(
        rng,
        players,
        [0] * count,
        1,
        categories=list(categories or DEFAULT_CATEGORIES),
        majority_invalid=majority_invalid,
    )


def _choose_dictator(rng: random.Random, player_count: int, previous: int | None = None) -> int:
    """Choose the round's dictator/letter chooser on the server.

    First round starts randomly. Later rounds rotate in seat order so every
    player gets exactly one letter choice before any player repeats.
    """
    if previous is not None and player_count > 1:
        return (previous + 1) % player_count
    return rng.randrange(player_count)


def _round(
    rng: random.Random,
    players: list[dict[str, Any]],
    scores: list[int],
    round_number: int,
    previous_dictator: int | None = None,
    categories: list[str] | None = None,
    majority_invalid: bool = True,
) -> dict[str, Any]:
    dictator = _choose_dictator(rng, len(players), previous_dictator)
    return {
        "game": "abc-fast-slow",
        "players": players,
        "player_count": len(players),
        "current_player": 0,
        "winner": None,
        "draw": False,
        "phase": "letter_picker",
        "round": round_number,
        "rounds": 3,
        "dictator_player": dictator,
        "letter_chooser": dictator,
        "letter": None,
        "categories": list(categories or DEFAULT_CATEGORIES),
        "majority_invalid": majority_invalid,
        "answers": [{} for _ in players],
        "scores": scores,
        "submitted": [False for _ in players],
        "votes": [{} for _ in players],
        "voted": [False for _ in players],
        "confirmed": [False for _ in players],
        "deadline": None,
        "picker_deadline": time.time() + PICKER_SECONDS,
        "picker_status": "idle",
        "picker_speed": None,
        "picker_started_at": None,
        "last_event": (
            f"Round {round_number}: {players[dictator]['name']} is the dictator. "
            "Choose a spin speed."
        ),
    }


def _start_picker(state: dict[str, Any], action: dict[str, Any]) -> None:
    speed = action.get("speed", "slow")
    if speed not in PICK_INTERVALS:
        raise IllegalMove("Choose fast or slow before starting the letter picker")
    state["picker_speed"] = speed
    state["picker_status"] = "running"
    state["picker_started_at"] = time.time()
    state["last_event"] = f"The letter wheel is spinning {speed}. Stop it when you are ready."
    state["phase"] = "letter_picker_running"


def _stop_picker(state: dict[str, Any]) -> None:
    if state.get("picker_status") != "running":
        raise IllegalMove("Start the letter picker first")
    started_at = float(state.get("picker_started_at") or time.time())
    elapsed = max(0.0, time.time() - started_at)
    interval = PICK_INTERVALS[str(state.get("picker_speed") or "slow")]
    state["letter"] = ALPHABET[int(elapsed / interval) % len(ALPHABET)]
    state["picker_status"] = "stopped"
    state["deadline"] = time.time() + ROUND_SECONDS
    state["phase"] = "answering"
    state["last_event"] = (
        f"Letter chosen: {state['letter']}. You have {ROUND_SECONDS} seconds to answer."
    )


def _auto_choose_letter(state: dict[str, Any]) -> None:
    """Recover a stalled picker so round never renders without a letter."""
    letter = state.get("letter")
    if not isinstance(letter, str) or letter not in ALPHABET:
        state["letter"] = random.choice(ALPHABET)
    state["picker_status"] = "stopped"
    state["deadline"] = time.time() + ROUND_SECONDS
    state["phase"] = "answering"
    state["last_event"] = (
        f"The letter chooser timed out. Letter {state['letter']} was selected automatically."
    )


def _submit(state: dict[str, Any], player: int, action: dict[str, Any]) -> None:
    if state["submitted"][player]:
        raise IllegalMove("You already submitted this round")
    raw = action.get("answers", {})
    if not isinstance(raw, dict):
        raw = {}
    categories = state.get("categories", list(DEFAULT_CATEGORIES))
    state["answers"][player] = {
        category: str(raw.get(category, "")).strip()[:40] for category in categories
    }
    state["submitted"][player] = True
    if all(state["submitted"]):
        _finish_answering(state)


def _finish_answering(state: dict[str, Any]) -> None:
    """Lock every unanswered sheet when shared answer time expires."""
    for player, submitted in enumerate(state["submitted"]):
        if not submitted:
            _submit(state, player, {})
    state["phase"] = "voting"
    state["deadline"] = None
    state["last_event"] = _voting_status(state)


def _voting_status(state: dict[str, Any]) -> str:
    voted = state.get("voted", [])
    confirmed = state.get("confirmed", [])
    waiting = [
        str(player.get("name", f"Player {index + 1}"))
        for index, player in enumerate(state.get("players", []))
        if index >= len(voted) or not voted[index]
    ]
    confirming = [
        str(player.get("name", f"Player {index + 1}"))
        for index, player in enumerate(state.get("players", []))
        if index < len(voted) and voted[index] and (index >= len(confirmed) or not confirmed[index])
    ]
    if waiting:
        return f"Still voting: {', '.join(waiting)}. Vote valid or invalid for each answer."
    if confirming:
        return f"Awaiting confirmation from: {', '.join(confirming)}."
    return "All players confirmed the results."


def _vote(state: dict[str, Any], player: int, action: dict[str, Any]) -> None:
    if state["voted"][player]:
        raise IllegalMove("You already voted this round")
    target = action.get("target")
    category = action.get("category")
    if not isinstance(target, int) or not 0 <= target < state["player_count"]:
        raise IllegalMove("Choose a player answer to review")
    if target == player:
        raise IllegalMove("You can only validate another player's answers")
    categories = state.get("categories", list(DEFAULT_CATEGORIES))
    if category not in categories:
        raise IllegalMove("Choose a valid category")
    state["votes"][player][f"{target}:{category}"] = bool(action.get("valid", False))
    # A single vote action represents the reviewer's complete ballot. This keeps
    # the game quick while still making every player participate in validation.
    required_votes = (state["player_count"] - 1) * len(categories)
    if len(state["votes"][player]) == required_votes:
        state["voted"][player] = True
    state["last_event"] = _voting_status(state)


def _confirm_results(state: dict[str, Any], player: int) -> None:
    if not state["voted"][player]:
        raise IllegalMove("Finish voting before confirming the results")
    if state["confirmed"][player]:
        raise IllegalMove("You already confirmed these results")
    state["confirmed"][player] = True
    if all(state["confirmed"]):
        _score_round(state)
    else:
        state["last_event"] = _voting_status(state)


def apply_abc_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    if not 0 <= player < state["player_count"]:
        raise IllegalMove("You are not a player in this game")
    kind = action.get("action", "submit")
    if kind == "play_again":
        if state.get("winner") is None and not state.get("draw"):
            raise IllegalMove("Finish the game before playing again")
        return _round(
            random.Random(),
            state["players"],
            list(state["scores"]),
            1,
            categories=list(state.get("categories", DEFAULT_CATEGORIES)),
            majority_invalid=bool(state.get("majority_invalid", True)),
        )
    if state.get("phase") == "letter_picker":
        if kind == "picker_timeout" and time.time() >= float(state.get("picker_deadline") or 0):
            _auto_choose_letter(state)
            return state
        if player != state.get("letter_chooser"):
            raise IllegalMove("Only the letter chooser can start the letter picker")
        if kind != "start_picker":
            raise IllegalMove("Choose fast or slow, then start the letter picker")
        _start_picker(state, action)
        return state
    if state.get("phase") == "letter_picker_running":
        if kind == "picker_timeout" and time.time() >= float(state.get("picker_deadline") or 0):
            _auto_choose_letter(state)
            return state
        if player != state.get("letter_chooser"):
            raise IllegalMove("Only the letter chooser can stop the letter picker")
        if kind != "stop_picker":
            raise IllegalMove("Stop the letter picker to choose the letter")
        _stop_picker(state)
        return state
    if state.get("phase") == "answering":
        expired = state.get("deadline") is not None and time.time() >= float(state["deadline"])
        if expired:
            if kind == "timeout" and not state["submitted"][player]:
                _submit(state, player, action)
            _finish_answering(state)
            return state
        if kind not in {"submit", "timeout"}:
            raise IllegalMove("Submit your answers before voting")
        if kind == "timeout" and not expired:
            raise IllegalMove("The round timer has not expired")
        _submit(state, player, {} if kind == "timeout" else action)
        return state
    if state.get("phase") == "voting":
        if kind == "vote":
            _vote(state, player, action)
        elif kind == "confirm_results":
            _confirm_results(state, player)
        else:
            raise IllegalMove("Review the answers, then confirm the results")
        return state
    raise IllegalMove("This round is already complete")


def _score_round(state: dict[str, Any]) -> None:
    letter = state["letter"].lower()
    categories = state.get("categories", list(DEFAULT_CATEGORIES))
    majority_invalid = bool(state.get("majority_invalid", True))
    accepted: dict[str, list[int]] = {category: [] for category in categories}
    breakdown: list[dict[str, Any]] = []
    for target, answers in enumerate(state["answers"]):
        for category in categories:
            value = answers.get(category, "").lower()
            key = f"{target}:{category}"
            approvals = sum(bool(ballot.get(key)) for ballot in state["votes"])
            validators = max(1, state["player_count"] - 1)
            invalid_votes = validators - approvals
            format_valid = bool(value and value.startswith(letter))
            rejected_by_majority = majority_invalid and invalid_votes > validators / 2
            accepted_answer = format_valid and not rejected_by_majority
            if accepted_answer:
                accepted[category].append(target)
            breakdown.append({
                "player": target,
                "category": category,
                "answer": answers.get(category, ""),
                "valid": accepted_answer,
                "votes_for": approvals,
                "votes_against": invalid_votes,
                "points": 0,
                "reason": "Pending duplicate check",
            })
    for category, targets in accepted.items():
        values = {target: state["answers"][target].get(category, "").strip().lower() for target in targets}
        for target, value in values.items():
            row = next(item for item in breakdown if item["player"] == target and item["category"] == category)
            if list(values.values()).count(value) == 1:
                state["scores"][target] += 10
                row.update(points=10, reason="Unique valid answer")
            else:
                row.update(valid=False, reason="Duplicate answer")
    for row in breakdown:
        if row["reason"] == "Pending duplicate check":
            row["reason"] = (
                "Rejected by majority"
                if row["votes_against"] > row["votes_for"]
                else "Does not start with the chosen letter"
            )
    state["round_breakdown"] = breakdown
    if state["round"] >= state["rounds"]:
        best = max(state["scores"])
        winners = [i for i, score in enumerate(state["scores"]) if score == best]
        state["winner"] = winners[0] if len(winners) == 1 else None
        state["draw"] = len(winners) > 1
        state["phase"] = "complete"
        state["last_event"] = "Game complete. The scoring breakdown is below."
    else:
        state["phase"] = "round_result"
        state["last_event"] = "Round complete. Review the scoring breakdown below."


def next_abc_round(state: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any]:
    if state.get("phase") != "round_result":
        raise IllegalMove("The round is not ready to continue")
    next_state = _round(
        rng or random.Random(),
        state["players"],
        list(state["scores"]),
        state["round"] + 1,
        int(state.get("dictator_player", state.get("letter_chooser", 0))),
        categories=list(state.get("categories", DEFAULT_CATEGORIES)),
        majority_invalid=bool(state.get("majority_invalid", True)),
    )
    state.clear()
    state.update(next_state)
    return state


def abc_bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    if state.get("phase") == "letter_picker" and player == state.get("letter_chooser"):
        return {"action": "start_picker", "speed": "slow"}
    if state.get("phase") == "letter_picker_running" and player == state.get("letter_chooser"):
        return {"action": "stop_picker"}
    if state.get("phase") == "answering":
        letter = state["letter"].lower()
        answers = {
            category: next((word for word in BOT_WORDS.get(category, ()) if word.startswith(letter)), "")
            for category in state.get("categories", DEFAULT_CATEGORIES)
        }
        return {"action": "submit", "answers": answers}
    if state.get("phase") == "voting":
        if state.get("voted", [])[player] and not state.get("confirmed", [])[player]:
            return {"action": "confirm_results"}
        # Bot accepts non-empty answers starting with the letter and rejects the rest.
        target, category = next(
            (candidate_target, candidate_category)
            for candidate_target in range(state["player_count"])
            if candidate_target != player
            for candidate_category in state.get("categories", DEFAULT_CATEGORIES)
            if f"{candidate_target}:{candidate_category}" not in state["votes"][player]
        )
        value = state["answers"][target].get(category, "").lower()
        return {
            "action": "vote",
            "target": target,
            "category": category,
            "valid": bool(value and value.startswith(state["letter"].lower())),
        }
    raise IllegalMove("The bot has no ABC action right now")
