import pytest

from app.games import multi
from app.games.connect_four import IllegalMove
from app.games.multi import apply_action, new_state
from app.games.universal import UniversalMatch


def test_ludo_roll_without_legal_move_passes_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 4)
    state = new_state("ludo")
    updated = apply_action(state, 0, {"action": "roll"})
    assert updated["roll"] == 4
    assert updated["positions"][0] == [-1, -1, -1, -1]
    assert updated["current_player"] == 1
    assert updated["phase"] == "roll"


def test_ludo_four_player_state_uses_every_reference_board_seat() -> None:
    state = new_state("ludo", player_count=4)
    assert state["player_count"] == 4
    assert [player["color"] for player in state["players"]] == ["red", "blue", "green", "yellow"]
    assert [player["offset"] for player in state["players"]] == [39, 0, 13, 26]
    assert len(state["positions"]) == len(state["captures"]) == len(state["last_rolls"]) == 4


def test_ludo_four_player_turn_visits_each_bot_then_returns_to_human(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 2)
    state = new_state("ludo", player_count=4)
    for expected_player in (1, 2, 3, 0):
        state = apply_action(state, state["current_player"], {"action": "roll"})
        assert state["current_player"] == expected_player


def test_ludo_six_releases_a_token_and_grants_another_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 6)
    state = apply_action(new_state("ludo"), 0, {"action": "roll"})
    assert state["phase"] == "move"
    assert state["legal_tokens"] == [0, 1, 2, 3]
    state = apply_action(state, 0, {"action": "move", "token": 2})
    assert state["positions"][0][2] == 0
    assert state["current_player"] == 0
    assert state["phase"] == "roll"


def test_ludo_capture_sends_an_opponent_home_and_grants_extra_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 3)
    state = new_state("ludo")
    state["positions"][0][0] = 4
    state["positions"][1][0] = 33  # Bot global cell 7; human lands there from 4 + 3.
    state = apply_action(state, 0, {"action": "roll"})
    state = apply_action(state, 0, {"action": "move", "token": 0})
    assert state["positions"][0][0] == 7
    assert state["positions"][1][0] == -1
    assert state["captures"] == [1, 0]
    assert state["current_player"] == 0
    assert state["phase"] == "roll"


def test_ludo_safe_spaces_protect_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 3)
    state = new_state("ludo")
    state["positions"][0][0] = 5
    state["positions"][1][0] = 34  # Both tokens meet on global safe cell 8.
    state = apply_action(state, 0, {"action": "roll"})
    state = apply_action(state, 0, {"action": "move", "token": 0})
    assert state["positions"][0][0] == 8
    assert state["positions"][1][0] == 34
    assert state["captures"] == [0, 0]


def test_ludo_three_consecutive_sixes_end_the_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 6)
    state = new_state("ludo")
    state["six_streak"] = 2
    state = apply_action(state, 0, {"action": "roll"})
    assert state["current_player"] == 1
    assert state["phase"] == "roll"
    assert state["legal_tokens"] == []
    assert state["positions"][0] == [-1, -1, -1, -1]


def test_ludo_requires_token_selection_before_another_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 6)
    state = apply_action(new_state("ludo"), 0, {"action": "roll"})
    with pytest.raises(IllegalMove, match="highlighted token"):
        apply_action(state, 0, {"action": "roll"})


def test_ludo_requires_an_exact_finish_and_rejects_unhighlighted_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 4)
    state = new_state("ludo")
    state["positions"][0] = [53, 56, 56, 56]
    state = apply_action(state, 0, {"action": "roll"})
    assert state["legal_tokens"] == []
    assert state["current_player"] == 1
    with pytest.raises(IllegalMove, match="not your turn"):
        apply_action(state, 0, {"action": "move", "token": 0})


def test_ludo_exact_finish_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 3)
    state = new_state("ludo")
    state["positions"][0] = [53, 56, 56, 56]
    state = apply_action(state, 0, {"action": "roll"})
    state = apply_action(state, 0, {"action": "move", "token": 0})
    assert state["positions"][0] == [56, 56, 56, 56]
    assert state["winner"] == 0
    assert state["phase"] == "finished"


def test_dominoes_start_with_valid_hands_and_turn() -> None:
    state = new_state("dominoes")
    assert len(state["hands"][0]) == 7
    assert len(state["hands"][1]) == 7
    tile = state["hands"][0][0]
    updated = apply_action(state, 0, {"tile_index": 0, "side": "right"})
    assert updated["board"] == [tile]
    assert updated["current_player"] == 1


def test_domino_snapshot_hides_bot_hands_but_exposes_counts() -> None:
    state = new_state("dominoes", player_count=4)
    match = UniversalMatch(
        id="domino-test",
        room_id=1,
        game_type="dominoes",
        state=state,
        player_ids={1: 0},
    )
    public_state = match.snapshot()["state"]
    assert len(public_state["hands"][0]) == 7
    assert public_state["hands"][1:] == [[], [], []]
    assert public_state["hand_counts"] == [7, 7, 7, 7]
    assert all(len(hand) == 7 for hand in state["hands"])


def test_four_player_dominoes_deals_every_tile_and_cycles_turns() -> None:
    state = new_state("dominoes", player_count=4)
    assert state["player_count"] == 4
    assert [len(hand) for hand in state["hands"]] == [7, 7, 7, 7]
    assert len({tuple(tile) for hand in state["hands"] for tile in hand}) == 28
    for expected_player in (1, 2, 3, 0):
        player = state["current_player"]
        move = state["legal_moves"][0] if state["legal_moves"] else None
        state = (
            apply_action(
                state,
                player,
                {"tile_index": move["tile_index"], "side": move["sides"][0]},
            )
            if move
            else apply_action(state, player, {"pass": True})
        )
        assert state["current_player"] == expected_player


def test_dominoes_orients_tiles_and_rejects_an_avoidable_pass() -> None:
    state = {
        **new_state("dominoes"),
        "hands": [[[2, 5], [0, 0]], [[1, 1]]],
        "board": [[5, 6]],
        "current_player": 0,
    }
    with pytest.raises(IllegalMove, match="still have"):
        apply_action(state, 0, {"pass": True})
    state = apply_action(state, 0, {"tile_index": 0, "side": "left"})
    assert state["board"] == [[2, 5], [5, 6]]
    assert state["last_move"]["tile"] == [2, 5]


def test_blocked_domino_round_uses_lowest_pip_total() -> None:
    state = {
        **new_state("dominoes"),
        "hands": [[[6, 6]], [[0, 1]]],
        "board": [[3, 3]],
        "current_player": 0,
        "passes": 1,
    }
    state = apply_action(state, 0, {"pass": True})
    assert state["winner"] == 1
    assert state["draw"] is False


def test_bingo_marks_drawn_numbers_and_trivia_scores() -> None:
    bingo = new_state("bingo")
    number = bingo["card"][0][0]
    bingo["remaining"] = [number]
    bingo = apply_action(bingo, 0, {"action": "draw"})
    assert bingo["marked"][0][0] is True
    trivia = new_state("trivia")
    trivia = apply_action(trivia, 0, {"answer": trivia["correct"], "response_ms": 1500})
    assert trivia["scores"][0] > 100
    assert trivia["phase"] == "bot"


def test_trivia_reveals_only_after_both_players_answer_and_advances() -> None:
    state = new_state("trivia")
    correct = state["correct"]
    state = apply_action(state, 0, {"answer": correct, "response_ms": 3000})
    state = apply_action(state, 1, {"answer": correct, "response_ms": 4500})
    assert state["phase"] == "reveal"
    assert state["selected_answers"] == [correct, correct]
    state = apply_action(state, 0, {"action": "next"})
    assert state["phase"] == "question"
    assert state["question_index"] == 1
    assert state["selected_answers"] == [None, None]


def test_trivia_snapshot_keeps_correct_answer_private_until_reveal() -> None:
    state = new_state("trivia")
    match = UniversalMatch(
        id="trivia-test",
        room_id=1,
        game_type="trivia",
        state=state,
        player_ids={1: 0},
    )
    assert "correct" not in match.snapshot()["state"]
    assert "correct_answer" not in match.snapshot()["state"]
    state = apply_action(state, 0, {"answer": state["correct"]})
    state = apply_action(state, 1, {"answer": state["correct"]})
    public_state = match.snapshot()["state"]
    assert "correct" not in public_state
    assert public_state["correct_answer"] == state["correct"]


def test_trivia_completes_all_five_questions_and_selects_a_winner() -> None:
    state = new_state("trivia")
    for index in range(5):
        correct = state["correct"]
        state = apply_action(state, 0, {"answer": correct})
        state = apply_action(state, 1, {"answer": (correct + 1) % 4})
        state = apply_action(state, 0, {"action": "next"})
        if index < 4:
            assert state["question_index"] == index + 1
    assert state["phase"] == "complete"
    assert state["winner"] == 0
    assert state["draw"] is False
