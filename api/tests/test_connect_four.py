import pytest

from app.games.connect_four import IllegalMove, apply_move, initial_state


def test_vertical_win_and_draw_state() -> None:
    state = initial_state()
    for column in (0, 1, 0, 1, 0, 1, 0):
        player = state.current_player
        state = apply_move(state, player, column)
    assert state.winner == 1
    assert state.move_count == 7


def test_rejects_wrong_turn_and_full_column() -> None:
    state = initial_state()
    with pytest.raises(IllegalMove, match="not your turn"):
        apply_move(state, 2, 0)
    for _ in range(6):
        state = apply_move(state, state.current_player, 0)
    with pytest.raises(IllegalMove, match="column is full"):
        apply_move(state, state.current_player, 0)


def test_diagonal_win() -> None:
    state = initial_state()
    for column in (0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3):
        state = apply_move(state, state.current_player, column)
    assert state.winner == 1
