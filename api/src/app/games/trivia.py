"""Server-authoritative Jeopardy-style trivia rounds."""

from __future__ import annotations

import random
import time
from typing import Any

from app.games.connect_four import IllegalMove

QUESTION_SECONDS = 15
ROUND_LENGTH = 15
POINT_VALUES = (100, 200, 300)

QUESTION_BANK: tuple[dict[str, Any], ...] = (
    {"category": "Wellbeing", "value": 100, "question": "Which practice helps bring attention back to the present moment?", "options": ["Grounding", "Rushing", "Multitasking", "Avoiding sleep"], "correct": 0},
    {"category": "Wellbeing", "value": 200, "question": "Which part of the body is most associated with a steady breathing exercise?", "options": ["Lungs", "Knees", "Ears", "Fingers"], "correct": 0},
    {"category": "Wellbeing", "value": 300, "question": "What is a helpful first step when a feeling becomes overwhelming?", "options": ["Name the feeling", "Hide it forever", "Skip every meal", "Ignore all support"], "correct": 0},
    {"category": "Animals", "value": 100, "question": "Which animal is known for having a long trunk?", "options": ["Elephant", "Penguin", "Rabbit", "Dolphin"], "correct": 0},
    {"category": "Animals", "value": 200, "question": "Which mammal is famous for fingerprints remarkably similar to humans?", "options": ["Koala", "Dolphin", "Owl", "Turtle"], "correct": 0},
    {"category": "Animals", "value": 300, "question": "What is a group of lions commonly called?", "options": ["A pride", "A school", "A swarm", "A pod"], "correct": 0},
    {"category": "Technology", "value": 100, "question": "What does CPU stand for?", "options": ["Central Processing Unit", "Computer Personal Utility", "Core Power User", "Central Program Upload"], "correct": 0},
    {"category": "Technology", "value": 200, "question": "Which device is primarily used to move a pointer on a computer screen?", "options": ["Mouse", "Router", "Printer", "Speaker"], "correct": 0},
    {"category": "Technology", "value": 300, "question": "What does HTML primarily describe?", "options": ["The structure of a web page", "A battery type", "A video format", "A computer virus"], "correct": 0},
    {"category": "Science", "value": 100, "question": "Which planet is famous for its visible rings?", "options": ["Mars", "Venus", "Saturn", "Mercury"], "correct": 2},
    {"category": "Science", "value": 200, "question": "How many notes are in a standard major scale before the octave repeats?", "options": ["Five", "Six", "Seven", "Eight"], "correct": 2},
    {"category": "Science", "value": 300, "question": "What force keeps people and objects on the ground?", "options": ["Gravity", "Magnetism", "Friction", "Sound"], "correct": 0},
    {"category": "Anime", "value": 100, "question": "In Pokémon, what kind of creature is Pikachu?", "options": ["A Pokémon", "A dragon", "A robot", "A wizard"], "correct": 0},
    {"category": "Anime", "value": 200, "question": "What is the name of the young ninja hero in Naruto?", "options": ["Naruto Uzumaki", "Goku", "Edward Elric", "Tanjiro Kamado"], "correct": 0},
    {"category": "Anime", "value": 300, "question": "In Spirited Away, what kind of place does Chihiro's family enter?", "options": ["A spirit world", "A space station", "A pirate ship", "A sports arena"], "correct": 0},
)

CATEGORIES = tuple(dict.fromkeys(question["category"] for question in QUESTION_BANK))
CLUES = {(question["category"], question["value"]): question for question in QUESTION_BANK}


def _load_question(state: dict[str, Any], category: str, value: int) -> None:
    question = CLUES[(category, value)]
    state.update(
        question=question["question"],
        question_index=len(state.get("used_clues", [])),
        options=list(question["options"]),
        category=category,
        value=value,
        clue_key=f"{category}:{value}",
        correct=question["correct"],
        phase="question",
        current_player=0,
        selected_answers=[None, None],
        answer_points=[0, 0],
        question_started_at=time.time(),
        deadline=time.time() + QUESTION_SECONDS,
        last_event=f"{value} points are on the line.",
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
        "categories": list(CATEGORIES),
        "point_values": list(POINT_VALUES),
        "board": [{"category": category, "values": list(POINT_VALUES)} for category in CATEGORIES],
        "used_clues": [],
        "clues": {f"{category}:{value}": question for (category, value), question in CLUES.items()},
        "scores": [0 for _ in range(player_count)],
        "streaks": [0 for _ in range(player_count)],
        "bot_players": list(bot_players),
        "players": [
            {"name": "You" if index == 0 else "Milo Bot", "is_bot": index in bot_players}
            for index in range(player_count)
        ],
        "action_count": 0,
        "phase": "board",
        "question": "Choose a category and point value.",
        "category": None,
        "value": None,
        "options": [],
        "selected_answers": [None, None],
        "answer_points": [0, 0],
        "deadline": None,
        "last_event": "Choose a category and point value.",
    }
    return state


def normalise_trivia_state(state: dict[str, Any]) -> None:
    """Upgrade early prototype sessions to the timed round contract."""
    if "board" in state and "clues" in state and "phase" in state:
        return
    replacement = new_trivia_state(random.Random(0))
    state.clear()
    state.update(replacement)


def apply_trivia_action(
    state: dict[str, Any], player: int, action: dict[str, Any]
) -> dict[str, Any]:
    if state["winner"] is not None or state.get("draw", False):
        raise IllegalMove("The trivia round is already finished")

    if state["phase"] == "board":
        if action.get("action") != "select_clue" or player != state.get("current_player"):
            raise IllegalMove("Choose a clue when it is your turn")
        category = str(action.get("category", ""))
        try:
            value = int(action.get("value"))
        except (TypeError, ValueError) as exc:
            raise IllegalMove("Choose a valid point value") from exc
        clue_key = f"{category}:{value}"
        if category not in state["categories"] or value not in POINT_VALUES or clue_key in state["used_clues"]:
            raise IllegalMove("That clue is not available")
        state["used_clues"].append(clue_key)
        _load_question(state, category, value)
        state["action_count"] += 1
        return state

    if state["phase"] == "reveal":
        # Either human may advance the shared reveal. The first request wins
        # under the match lock, which keeps human-vs-human rooms responsive.
        if action.get("action") != "next":
            raise IllegalMove("Continue when you are ready")
        if len(state["used_clues"]) >= int(state["question_count"]):
            state["phase"] = "complete"
            if state["scores"][0] == state["scores"][1]:
                state["draw"] = True
                state["last_event"] = "A tie — sharp minds think alike!"
            else:
                state["winner"] = 0 if state["scores"][0] > state["scores"][1] else 1
                state["last_event"] = f"{state['players'][state['winner']]['name']} won the quiz!"
            state["action_count"] += 1
            return state
        state["phase"] = "board"
        state["question"] = "Choose a category and point value."
        state["category"] = None
        state["value"] = None
        state["options"] = []
        state["selected_answers"] = [None, None]
        state["answer_points"] = [0, 0]
        state["deadline"] = None
        state["last_event"] = f"{state['players'][state['current_player']]['name']} chooses the next clue."
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
        points = int(state["value"])
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
    if state.get("phase") == "board":
        available = [
            (category, value)
            for category in state.get("categories", [])
            for value in POINT_VALUES
            if f"{category}:{value}" not in state.get("used_clues", [])
        ]
        category, value = max(available, key=lambda clue: clue[1])
        return {"action": "select_clue", "category": category, "value": value}
    # Friendly but capable: Milo misses every fifth clue, making the round fair.
    correct = int(state["correct"])
    answer = (correct + 1) % 4 if int(state["question_index"]) % 5 == 4 else correct
    return {"answer": answer, "response_ms": 4200 + int(state["question_index"]) * 350}
