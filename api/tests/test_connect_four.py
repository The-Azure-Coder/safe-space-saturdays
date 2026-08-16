from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest

from app.games.connect_four import IllegalMove, apply_move, choose_bot_column, initial_state
from app.games.manager import MatchManager


def test_vertical_win_and_draw_state() -> None:
    state = initial_state()
    for column in (0, 1, 0, 1, 0, 1, 0):
        player = state.current_player
        state = apply_move(state, player, column)
    assert state.winner == 1
    assert state.move_count == 7
    assert state.last_move == (2, 0)
    assert state.winning_cells == ((2, 0), (3, 0), (4, 0), (5, 0))


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


def test_thoughtful_bot_takes_a_win_and_blocks_the_player() -> None:
    state = initial_state()
    for column in (0, 6, 1, 6, 4, 6, 5):
        state = apply_move(state, state.current_player, column)
    assert choose_bot_column(state, 2, "thoughtful") == 6

    block_state = initial_state()
    for column in (0, 6, 1, 6, 2):
        block_state = apply_move(block_state, block_state.current_player, column)
    block_state = replace(block_state, current_player=2)
    assert choose_bot_column(block_state, 2, "thoughtful") == 3


def test_bot_filling_does_not_replace_a_second_human() -> None:
    manager = MatchManager()
    match = manager.create(1, 101, True, "friendly", {101: 0, 202: 1})

    assert match.bot_player is None
    assert match.player_ids == {101: 1, 202: 2}


@pytest.mark.asyncio
async def test_play_again_alternates_the_starting_player() -> None:
    manager = MatchManager()
    match = manager.create(1, 101, True, "friendly")
    match.state = replace(match.state, winner=1)

    with patch("app.games.manager.asyncio.sleep", new=AsyncMock()):
        await manager.play_again(match, 101)

    assert match.starting_player == 2
    assert match.state.move_count == 1  # bot takes the opening move
    assert match.state.current_player == 1  # human gets control after the bot opens

    match.state = replace(match.state, winner=1)
    with patch("app.games.manager.asyncio.sleep", new=AsyncMock()):
        await manager.play_again(match, 101)

    assert match.starting_player == 1
    assert match.state.current_player == 1
