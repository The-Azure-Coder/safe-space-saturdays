from app.games.connect_four import IllegalMove
from app.games.multi import apply_action, new_state


def test_ludo_requires_a_six_to_leave_base() -> None:
    state = new_state("ludo")
    # A random roll is server-owned; either the token moves or the action is rejected.
    try:
        updated = apply_action(state, 0, {"token": 0})
    except IllegalMove as error:
        assert "six" in str(error)
    else:
        assert updated["positions"][0][0] == 0
        assert updated["roll"] == 6


def test_dominoes_start_with_valid_hands_and_turn() -> None:
    state = new_state("dominoes")
    assert len(state["hands"][0]) == 7
    assert len(state["hands"][1]) == 7
    tile = state["hands"][0][0]
    updated = apply_action(state, 0, {"tile_index": 0, "side": "right"})
    assert updated["board"] == [tile]
    assert updated["current_player"] == 1


def test_bingo_marks_drawn_numbers_and_trivia_scores() -> None:
    bingo = new_state("bingo")
    number = bingo["card"][0][0]
    bingo["remaining"] = [number]
    bingo = apply_action(bingo, 0, {"action": "draw"})
    assert bingo["marked"][0][0] is True
    trivia = new_state("trivia")
    trivia = apply_action(trivia, 0, {"answer": 1})
    assert trivia["scores"][0] == 100
