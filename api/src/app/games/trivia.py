"""Server-authoritative timed trivia rounds."""

from __future__ import annotations

import random
import time
from typing import Any

from app.games.connect_four import IllegalMove

QUESTION_SECONDS = 15
ROUND_LENGTH = 5

QUESTION_BANK: tuple[dict[str, Any], ...] = (
    {
        "category": "Wellbeing",
        "question": "Which practice can help you return attention to the present moment?",
        "options": ["Grounding", "Rushing", "Multitasking", "Avoiding sleep"],
        "correct": 0,
    },
    {
        "category": "Nature",
        "question": "What is the largest living structure visible from space?",
        "options": ["Amazon rainforest", "Great Barrier Reef", "Sahara Desert", "Himalayas"],
        "correct": 1,
    },
    {
        "category": "Music",
        "question": "How many notes are in a standard major scale before the octave repeats?",
        "options": ["Five", "Six", "Seven", "Eight"],
        "correct": 2,
    },
    {
        "category": "Jamaica",
        "question": "Which Jamaican city is known as the birthplace of reggae music?",
        "options": ["Kingston", "Montego Bay", "Port Antonio", "Mandeville"],
        "correct": 0,
    },
    {
        "category": "Science",
        "question": "Which planet is famous for its visible rings?",
        "options": ["Mars", "Venus", "Saturn", "Mercury"],
        "correct": 2,
    },
    {
        "category": "Words",
        "question": "What does the word ‘resilient’ most closely mean?",
        "options": ["Able to recover", "Unable to change", "Always silent", "Quick to judge"],
        "correct": 0,
    },
    {
        "category": "Animals",
        "question": "Which animal has fingerprints remarkably similar to humans?",
        "options": ["Koala", "Dolphin", "Owl", "Turtle"],
        "correct": 0,
    },
    {
        "category": "Food",
        "question": "Which fruit is traditionally used to make guacamole?",
        "options": ["Plantain", "Avocado", "Mango", "Lime"],
        "correct": 1,
    },
)


def _load_question(state: dict[str, Any], index: int) -> None:
    question = QUESTION_BANK[state["question_ids"][index]]
    state.update(
        question=question["question"],
        options=list(question["options"]),
        category=question["category"],
        correct=question["correct"],
        phase="question",
        current_player=0,
        selected_answers=[None, None],
        answer_points=[0, 0],
        question_started_at=time.time(),
        deadline=time.time() + QUESTION_SECONDS,
        last_event="Choose the answer that feels right.",
    )


def new_trivia_state(
    rng: random.Random, player_count: int = 2, bot_players: tuple[int, ...] = (1,)
) -> dict[str, Any]:
    player_count = max(2, min(2, player_count))
    state: dict[str, Any] = {
        "game": "trivia",
        "current_player": 0,
        "winner": None,
        "draw": False,
        "question_index": 0,
        "question_count": ROUND_LENGTH,
        "question_ids": rng.sample(range(len(QUESTION_BANK)), ROUND_LENGTH),
        "scores": [0 for _ in range(player_count)],
        "streaks": [0 for _ in range(player_count)],
        "bot_players": list(bot_players),
        "players": [
            {"name": "You" if index == 0 else "Milo Bot", "is_bot": index in bot_players}
            for index in range(player_count)
        ],
        "action_count": 0,
    }
    _load_question(state, 0)
    return state


def normalise_trivia_state(state: dict[str, Any]) -> None:
    """Upgrade early prototype sessions to the timed round contract."""
    if "question_ids" in state and "phase" in state:
        return
    replacement = new_trivia_state(random.Random(0))
    state.clear()
    state.update(replacement)


def apply_trivia_action(
    state: dict[str, Any], player: int, action: dict[str, Any]
) -> dict[str, Any]:
    if state["winner"] is not None or state.get("draw", False):
        raise IllegalMove("The trivia round is already finished")

    if state["phase"] == "reveal":
        # Either human may advance the shared reveal. The first request wins
        # under the match lock, which keeps human-vs-human rooms responsive.
        if action.get("action") != "next":
            raise IllegalMove("Continue when you are ready")
        next_index = int(state["question_index"]) + 1
        if next_index >= int(state["question_count"]):
            state["phase"] = "complete"
            if state["scores"][0] == state["scores"][1]:
                state["draw"] = True
                state["last_event"] = "A tie — sharp minds think alike!"
            else:
                state["winner"] = 0 if state["scores"][0] > state["scores"][1] else 1
                state["last_event"] = f"{state['players'][state['winner']]['name']} won the quiz!"
            state["action_count"] += 1
            return state
        state["question_index"] = next_index
        _load_question(state, next_index)
        state["action_count"] += 1
        return state

    if state["phase"] not in {"question", "bot"} or state["current_player"] != player:
        raise IllegalMove("It is not your turn")
    answer = action.get("answer")
    if not isinstance(answer, int) or not -1 <= answer < 4:
        raise IllegalMove("Choose one answer")

    correct = answer == state["correct"]
    if player in state.get("bot_players", []) and time.time() > state["deadline"]:
        answer = -1
    if (
        player not in state.get("bot_players", [])
        and time.time() > state["deadline"]
        and answer != -1
    ):
        raise IllegalMove("Question time expired")
    if correct:
        state["streaks"][player] += 1
        elapsed_ms = max(
            0,
            int(action.get("response_ms", 0))
            if player in state.get("bot_players", [])
            else int((time.time() - state["question_started_at"]) * 1000),
        )
        speed_bonus = max(0, 100 - elapsed_ms // 150)
        points = 100 + speed_bonus + min(60, (state["streaks"][player] - 1) * 20)
        state["scores"][player] += points
        state["answer_points"][player] = points
    else:
        state["streaks"][player] = 0
        state["answer_points"][player] = 0
    state["selected_answers"][player] = answer
    state["action_count"] += 1

    if player == 0 and 1 in state.get("bot_players", []):
        state["phase"] = "bot"
        state["current_player"] = 1
        state["last_event"] = "Answer locked. Milo is choosing…"
    elif player == 0:
        state["phase"] = "question"
        state["current_player"] = 1
        state["last_event"] = "Answer locked. Your opponent is choosing…"
    else:
        state["phase"] = "reveal"
        state["current_player"] = player
        state["last_event"] = (
            "Correct!"
            if state["selected_answers"][0] == state["correct"]
            else "Good try — here is the answer."
        )
    return state


def trivia_bot_action(state: dict[str, Any]) -> dict[str, Any]:
    # Friendly but capable: Milo misses every fifth question, making the round fair.
    correct = int(state["correct"])
    answer = (correct + 1) % 4 if int(state["question_index"]) % 5 == 4 else correct
    return {"answer": answer, "response_ms": 4200 + int(state["question_index"]) * 350}
