import pytest

from app.games.connect_four import IllegalMove
import app.games.csec_exam as csec_exam
from app.routes.api import can_access_csec_exam
from app.games.csec_exam import PAPER_ONE, PAPER_TWO, apply_csec_exam_action, new_csec_exam_state


def test_paper_one_scores_and_opens_paper_two() -> None:
    state = new_csec_exam_state(2)
    assert state["started_at"] is not None
    for index, question in enumerate(PAPER_ONE):
        apply_csec_exam_action(
            state,
            0,
            {"action": "answer_one", "question_index": index, "answer": question["correct"]},
        )
    assert state["phase"] == "paper_two"
    assert state["paper_one_scores"] == [30, 0]
    apply_csec_exam_action(state, 0, {"action": "submit_exam"})
    assert state["submitted_at"] is not None
    assert state["time_spent_seconds"] >= 0
    assert len(state["paper_one_breakdown"]) == len(PAPER_ONE)
    assert state["paper_one_breakdown"][0]["correct"] == PAPER_ONE[0]["options"][PAPER_ONE[0]["correct"]]


def test_paper_two_answers_are_saved_and_teacher_can_grade() -> None:
    state = new_csec_exam_state(2)
    state["players"][0]["name"] = "Tyrese"
    apply_csec_exam_action(
        state,
        1,
        {
            "action": "answer_two",
            "question_id": "1a",
            "answer": "CPU, RAM, storage and input devices.",
        },
    )
    apply_csec_exam_action(
        state,
        0,
        {
            "action": "grade_two",
            "target_player": 1,
            "question_id": "1a",
            "points": 4,
            "feedback": "Good coverage.",
        },
    )
    assert state["answers_two"][1][0].startswith("CPU")
    assert state["paper_two_scores"][1] == 4
    assert state["grades"][1][0]["feedback"] == "Good coverage."


def test_non_teacher_cannot_grade_and_points_are_bounded() -> None:
    state = new_csec_exam_state(2)
    with pytest.raises(IllegalMove, match="Only Tyrese"):
        apply_csec_exam_action(
            state, 0, {"action": "grade_two", "target_player": 1, "question_id": "1a", "points": 1}
        )
    state["players"][0]["name"] = "Tyrese"
    with pytest.raises(IllegalMove, match="within"):
        apply_csec_exam_action(
            state,
            0,
            {
                "action": "grade_two",
                "target_player": 1,
                "question_id": "1a",
                "points": PAPER_TWO[0]["marks"] + 1,
            },
        )


def test_exam_auto_submits_when_two_hour_deadline_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    state = new_csec_exam_state(1)
    state["deadline_at"] = 100.0
    monkeypatch.setattr(csec_exam.time, "time", lambda: 101.0)
    apply_csec_exam_action(state, 0, {"action": "answer_one", "question_index": 0, "answer": 0})
    assert state["phase"] == "complete"
    assert state["submitted_at"] == 101.0
    assert state["time_spent_seconds"] == csec_exam.EXAM_DURATION_SECONDS
    assert len(state["paper_one_breakdown"]) == len(PAPER_ONE)


def test_invited_users_can_access_private_exam() -> None:
    class UserStub:
        def __init__(self, name: str) -> None:
            self.name = name

    assert can_access_csec_exam(UserStub("Tushaii"))
    assert not can_access_csec_exam(UserStub("Someone Else"))
