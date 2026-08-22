import pytest

from app.games.connect_four import IllegalMove
from app.games.together import LEVELS, apply_together_action, new_together_state


def move_to_finish(state: dict, seat: int) -> None:
    while state["players"][seat]["x"] < state["level_config"]["finish"]:
        apply_together_action(state, seat, {"action": "input", "axis": 1, "dt": 0.12})


def test_together_scales_for_two_three_and_four_players() -> None:
    for count in (2, 3, 4):
        state = new_together_state(count)
        assert state["player_count"] == count
        assert len(state["players"]) == count
        assert len(state["switches"]) == count


def test_finish_requires_every_connected_player() -> None:
    state = new_together_state(2)
    move_to_finish(state, 0)
    with pytest.raises(IllegalMove, match="Everyone"):
        apply_together_action(state, 0, {"action": "finish"})
    move_to_finish(state, 1)
    apply_together_action(state, 0, {"action": "finish"})
    assert state["level"] == 2
    assert state["levels_completed"] == 1


def test_checkpoint_and_fall_are_authoritative() -> None:
    state = new_together_state(2)
    while state["players"][0]["x"] < state["level_config"]["checkpoint"]:
        apply_together_action(state, 0, {"action": "input", "axis": 1, "dt": 0.12})
    assert state["checkpoint_reached"] is True
    checkpoint = state["players"][0]["checkpoint"]
    apply_together_action(state, 0, {"action": "fall"})
    assert state["players"][0]["x"] == checkpoint
    assert state["falls"] == 1


def test_all_twenty_levels_can_complete_as_a_team() -> None:
    state = new_together_state(2)
    for _ in range(len(LEVELS)):
        move_to_finish(state, 0)
        move_to_finish(state, 1)
        apply_together_action(state, 0, {"action": "finish"})
    assert state["phase"] == "complete"
    assert state["levels_completed"] == 20
    assert state["last_event"] == "WE MADE IT!"
