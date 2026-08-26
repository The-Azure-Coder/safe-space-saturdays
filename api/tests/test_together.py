import pytest

from app.games.connect_four import IllegalMove
from app.games.together import LEVELS, apply_together_action, new_together_state


def move_to_finish(state: dict, seat: int) -> None:
    while state["players"][seat]["x"] < state["level_config"]["finish"]:
        before = state["players"][seat]["x"]
        apply_together_action(state, seat, {"action": "input", "axis": 1, "dt": 0.12})
        if state["players"][seat]["x"] <= before:
            apply_together_action(
                state, seat, {"action": "input", "axis": 1, "jump": True, "dt": 0.12}
            )


def test_together_scales_for_two_through_five_players() -> None:
    for count in (2, 3, 4, 5):
        state = new_together_state(count)
        assert state["player_count"] == count
        assert len(state["players"]) == count
        assert len(state["switches"]) == count


def test_together_supports_a_single_player_session() -> None:
    state = new_together_state(1)

    assert state["player_count"] == 1
    assert len(state["players"]) == 1
    state["finishers"] = [0]
    apply_together_action(state, 0, {"action": "finish"})
    assert state["levels_completed"] == 1


def test_block_robots_can_stand_on_each_other() -> None:
    state = new_together_state(2)
    lower, upper = state["players"]
    lower["x"], lower["y"] = 300, 0
    upper["x"], upper["y"], upper["vy"], upper["on_ground"] = 300, 90, -120, False

    apply_together_action(state, 1, {"action": "input", "axis": 0, "dt": 0.12})

    assert upper["y"] == 72
    assert upper["on_ground"] is True


def test_block_robots_do_not_pass_through_on_same_tier() -> None:
    state = new_together_state(2)
    left, right = state["players"]
    left["x"], right["x"] = 300, 348

    apply_together_action(state, 0, {"action": "input", "axis": 1, "dt": 0.12})

    assert left["x"] <= 300


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
        before = state["players"][0]["x"]
        apply_together_action(state, 0, {"action": "input", "axis": 1, "dt": 0.12})
        if state["players"][0]["x"] <= before:
            apply_together_action(
                state, 0, {"action": "input", "axis": 1, "jump": True, "dt": 0.12}
            )
    assert state["checkpoint_reached"] is True
    checkpoint = state["players"][0]["checkpoint"]
    apply_together_action(state, 0, {"action": "fall"})
    assert state["players"][0]["x"] == checkpoint
    assert state["falls"] == 1


def test_jump_has_real_arc_with_buffered_input() -> None:
    state = new_together_state(2)
    apply_together_action(state, 0, {"action": "input", "axis": 0, "jump": True, "dt": 0.066})
    assert state["players"][0]["y"] > 0
    assert state["players"][0]["on_ground"] is False


def test_authoritative_physics_lands_on_an_elevated_platform() -> None:
    state = new_together_state(2)
    platform = state["level_config"]["platforms"][0]
    player = state["players"][0]
    player["x"] = platform["x"]
    player["y"] = platform["y"] + 12
    player["vy"] = -120
    player["on_ground"] = False
    apply_together_action(state, 0, {"action": "input", "axis": 0, "dt": 0.12})
    assert player["y"] == platform["y"]
    assert player["on_ground"] is True


def test_all_twenty_levels_can_complete_as_a_team() -> None:
    state = new_together_state(2)
    for _ in range(len(LEVELS)):
        move_to_finish(state, 0)
        move_to_finish(state, 1)
        apply_together_action(state, 0, {"action": "finish"})
    assert state["phase"] == "complete"
    assert state["levels_completed"] == 20
    assert state["last_event"] == "WE MADE IT!"
