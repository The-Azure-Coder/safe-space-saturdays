import pytest

from app.games.checkers import (
    _search_depth_for_level,
    apply_checkers_action,
    checkers_bot_action,
    legal_moves,
    new_checkers_state,
)
from app.games.connect_four import IllegalMove


def test_checkers_starts_with_two_players_and_twelve_pieces_each() -> None:
    state = new_checkers_state(bot_players=())
    assert state["player_count"] == 2
    assert sum(piece == 1 for row in state["board"] for piece in row) == 12
    assert sum(piece == 2 for row in state["board"] for piece in row) == 12
    assert len(state["legal_moves"]) == 7


def test_checkers_forces_capture_and_promotes_a_piece() -> None:
    state = new_checkers_state(bot_players=())
    state["board"] = [[0] * 8 for _ in range(8)]
    state["board"][2][1] = 1
    state["board"][1][2] = 2
    state["legal_moves"] = [{"from": [2, 1], "to": [0, 3], "capture": [1, 2]}]
    apply_checkers_action(state, 0, {"action": "move", "move": {"from": [2, 1], "to": [0, 3]}})
    assert state["board"][0][3] == 3
    assert state["current_player"] == 1


def test_checkers_rejects_quiet_move_when_capture_exists() -> None:
    state = new_checkers_state(bot_players=())
    state["board"] = [[0] * 8 for _ in range(8)]
    state["board"][5][0] = 1
    state["board"][4][1] = 2
    state["board"][5][2] = 1
    with pytest.raises(IllegalMove, match="not legal"):
        apply_checkers_action(state, 0, {"action": "move", "move": {"from": [5, 2], "to": [4, 3]}})


def test_checkers_bot_chooses_a_legal_move() -> None:
    state = new_checkers_state()
    move = checkers_bot_action(state, 1)
    assert move["action"] == "move"
    assert move["move"] in [
        {"from": item["from"], "to": item["to"]} for item in legal_moves(state, 1)
    ]


def test_checkers_search_depth_scales_until_the_strongest_tier() -> None:
    assert [_search_depth_for_level(level) for level in range(2, 6)] == [2, 3, 4, 4]
    assert _search_depth_for_level(5, piece_count=16) == 5


def test_higher_level_checkers_bot_avoids_an_immediate_capture() -> None:
    state = new_checkers_state(bot_players=(1,))
    state["board"] = [[0 for _ in range(8)] for _ in range(8)]
    state["board"][2][1] = 2
    state["board"][4][3] = 1
    state["current_player"] = 1
    state["legal_moves"] = legal_moves(state, 1)

    move = checkers_bot_action(state, 1, "thoughtful", level=3)

    assert move["move"] == {"from": [2, 1], "to": [3, 0]}
