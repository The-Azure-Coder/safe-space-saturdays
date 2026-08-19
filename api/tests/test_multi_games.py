import time

import pytest

from app.games import multi
from app.games.connect_four import IllegalMove
from app.games.multi import apply_action, bot_action, new_state, normalise_domino_state, normalise_ludo_state
from app.games.scribble import WORDS, progressive_hint
from app.games.universal import UniversalMatch
from app.games.abc_fast_slow import CATEGORIES, new_abc_state, next_abc_round


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
    assert [player["offset"] for player in state["players"]] == [0, 39, 13, 26]
    assert len(state["positions"]) == len(state["captures"]) == len(state["last_rolls"]) == 4


def test_ludo_normalisation_preserves_human_player_metadata_after_an_action() -> None:
    state = new_state("ludo", player_count=2, bot_players=())
    state["players"][0]["name"] = "Jack"
    state["players"][0]["is_bot"] = False
    state["players"][1]["name"] = "Tatty"
    state["players"][1]["is_bot"] = False
    normalise_ludo_state(state)
    assert [(player["name"], player["is_bot"]) for player in state["players"]] == [
        ("Jack", False),
        ("Tatty", False),
    ]


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


def test_abc_fast_or_slow_submits_reviews_scores_and_advances() -> None:
    state = new_state("abc-fast-slow", player_count=2, bot_players=(1,))
    apply_action(state, 0, {"action": "start_picker", "speed": "slow"})
    state["picker_started_at"] = time.time() - 1
    apply_action(state, 0, {"action": "stop_picker"})
    bot_submission = bot_action(state, 1)
    apply_action(state, 0, {"action": "submit", "answers": bot_submission["answers"]})
    apply_action(state, 1, bot_submission)
    assert state["phase"] == "voting"
    for player in (0, 1):
        for target in range(2):
            if target == player:
                continue
            for category in CATEGORIES:
                action = {"action": "vote", "target": target, "category": category, "valid": True}
                apply_action(state, player, action)
    assert state["phase"] == "round_result"
    assert state["scores"] == [0, 0]  # identical answers are duplicates
    apply_action(state, 0, {"action": "next_round"})
    assert state["phase"] == "letter_picker"
    assert state["round"] == 2


def test_abc_human_players_validate_only_each_other_and_advance() -> None:
    state = new_state("abc-fast-slow", player_count=2, bot_players=())
    apply_action(state, 0, {"action": "start_picker", "speed": "slow"})
    state["picker_started_at"] = time.time() - 1
    apply_action(state, 0, {"action": "stop_picker"})
    answers = {category: "apple" for category in CATEGORIES}
    apply_action(state, 0, {"action": "submit", "answers": answers})
    apply_action(state, 1, {"action": "submit", "answers": answers})
    with pytest.raises(IllegalMove, match="another player's"):
        apply_action(state, 0, {"action": "vote", "target": 0, "category": "Animal", "valid": True})
    for player, target in ((0, 1), (1, 0)):
        for category in CATEGORIES:
            apply_action(state, player, {"action": "vote", "target": target, "category": category, "valid": True})
    assert state["phase"] == "round_result"
    apply_action(state, 1, {"action": "next_round"})
    assert state["phase"] == "letter_picker"
    assert state["round"] == 2


def test_abc_selects_a_random_dictator_and_rotates_the_letter_chooser() -> None:
    class PredictableRandom:
        def __init__(self) -> None:
            self.letters = iter(("A", "B"))

        def choice(self, _sequence: str) -> str:
            return next(self.letters)

        def randrange(self, _stop: int) -> int:
            return 0

    rng = PredictableRandom()
    state = new_abc_state(rng, player_count=2, bot_players=())
    assert state["letter"] is None
    assert state["dictator_player"] == 0
    assert state["letter_chooser"] == 0
    state["phase"] = "round_result"
    next_abc_round(state, rng)
    assert state["letter"] is None
    assert state["phase"] == "letter_picker"
    assert state["dictator_player"] == 1
    assert state["letter_chooser"] == 1


def test_abc_timeout_locks_blank_answers() -> None:
    state = new_state("abc-fast-slow", player_count=2, bot_players=())
    apply_action(state, 0, {"action": "start_picker", "speed": "slow"})
    state["picker_started_at"] = time.time() - 1
    apply_action(state, 0, {"action": "stop_picker"})
    assert state["letter"] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    state["deadline"] = 0
    apply_action(state, 0, {"action": "timeout"})
    assert state["submitted"][0] is True
    assert state["answers"][0] == {category: "" for category in CATEGORIES}


def test_ludo_capture_sends_an_opponent_home_and_grants_extra_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 3)
    state = new_state("ludo")
    state["positions"][0][0] = 4
    state["positions"][1][0] = 46  # Green bot global cell 7; human lands there from 4 + 3.
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
    state["positions"][0] = [54, 57, 57, 57]
    state = apply_action(state, 0, {"action": "roll"})
    assert state["legal_tokens"] == []
    assert state["current_player"] == 1
    with pytest.raises(IllegalMove, match="not your turn"):
        apply_action(state, 0, {"action": "move", "token": 0})


def test_ludo_exact_finish_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 3)
    state = new_state("ludo")
    state["positions"][0] = [54, 57, 57, 57]
    state = apply_action(state, 0, {"action": "roll"})
    state = apply_action(state, 0, {"action": "move", "token": 0})
    assert state["positions"][0] == [57, 57, 57, 57]
    assert state["winner"] == 0
    assert state["phase"] == "finished"


def test_ludo_one_enters_home_from_the_last_lane_space(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(multi, "_roll_die", lambda: 1)
    state = new_state("ludo")
    state["positions"][0] = [56, 57, 57, 57]
    state = apply_action(state, 0, {"action": "roll"})
    assert state["legal_tokens"] == [0]
    state = apply_action(state, 0, {"action": "move", "token": 0})
    assert state["positions"][0][0] == multi.LUDO_FINISH


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
    normalise_domino_state(state)
    with pytest.raises(IllegalMove, match="still have"):
        apply_action(state, 0, {"pass": True})
    state = apply_action(state, 0, {"tile_index": 0, "side": "left"})
    assert state["board"] == [[2, 5], [5, 6]]
    assert state["last_move"]["tile"] == [2, 5]


def test_dominoes_rejects_the_wrong_open_end() -> None:
    state = {
        **new_state("dominoes"),
        "hands": [[[1, 2], [4, 5]], [[0, 0]]],
        "board": [[5, 6]],
        "current_player": 0,
    }
    normalise_domino_state(state)
    assert state["legal_moves"] == [{"tile_index": 1, "sides": ["left"]}]
    with pytest.raises(IllegalMove, match="does not match"):
        apply_action(state, 0, {"tile_index": 1, "side": "right"})
    updated = apply_action(state, 0, {"tile_index": 1, "side": "left"})
    assert updated["board"] == [[4, 5], [5, 6]]


def test_blocked_domino_round_uses_lowest_pip_total() -> None:
    state = {
        **new_state("dominoes"),
        "hands": [[[6, 6]], [[0, 1]]],
        "board": [[3, 3]],
        "current_player": 0,
        "passes": 1,
    }
    state = apply_action(state, 0, {"pass": True})
    assert state["round_winner"] == 1
    assert state["round"] == 2
    assert state["starting_player"] == 1
    assert state["draw"] is False


def test_scribble_hides_word_from_guesser_and_scores_correct_guess() -> None:
    state = new_state("scribble", player_count=2, bot_players=(1,))
    match = UniversalMatch(id="scribble-test", room_id=1, game_type="scribble", state=state, player_ids={1: 0, 2: 1})
    assert match.snapshot(2)["state"].get("word") is None
    state = apply_action(state, 0, {"action": "choose_word", "word": state["word_choices"][0]})
    state = apply_action(state, 0, {"action": "stroke", "points": [{"x": 0.1, "y": 0.1}, {"x": 0.8, "y": 0.8}]})
    state = apply_action(state, 0, {"action": "end_turn"})
    state = apply_action(state, 1, {"action": "guess", "text": state["word"]})
    assert state["scores"] == [50, 100]
    assert state["phase"] == "round_result"
    state = apply_action(state, 0, {"action": "continue"})
    assert state["round"] == 2
    assert state["current_drawer"] == 1
    assert state["word"] in WORDS


def test_scribble_bot_can_draw_after_human_guesses() -> None:
    state = new_state("scribble", player_count=2, bot_players=(1,))
    state = apply_action(state, 0, {"action": "choose_word", "word": state["word_choices"][0]})
    state = apply_action(state, 0, {"action": "end_turn"})
    state = apply_action(state, 1, {"action": "guess", "text": "wrong"})
    assert state["guesses"][-1]["correct"] is False
    state["round"] = 2
    state["current_drawer"] = 1
    state["current_player"] = 1
    state["bot_draw_pending"] = True
    state = apply_action(state, 1, bot_action(state, 1))
    assert state["phase"] == "guessing"
    assert state["strokes"]


def test_scribble_word_choice_preview_warm_guess_and_timeout() -> None:
    state = new_state("scribble", player_count=2, bot_players=())
    assert len(state["word_choices"]) == 3
    word = state["word_choices"][0]
    state = apply_action(state, 0, {"action": "choose_word", "word": word})
    state = apply_action(state, 0, {"action": "stroke_preview", "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.4}]})
    assert state["live_stroke"]["points"]
    state = apply_action(state, 0, {"action": "stroke_segment", "points": [{"x": 0.1, "y": 0.1}, {"x": 0.4, "y": 0.4}], "color": "#1f2421", "size": 6, "erase": True})
    assert state["strokes"][-1]["erase"] is True
    before_clear = state["action_count"]
    state = apply_action(state, 0, {"action": "clear"})
    assert state["strokes"] == []
    assert state["action_count"] == before_clear + 1
    state = apply_action(state, 0, {"action": "end_turn"})
    state["word"] = "cat"
    state["guess_deadline"] = 9_999_999_999
    state = apply_action(state, 1, {"action": "guess", "text": "car"})
    assert state["guesses"][-1]["warm"] is True
    state = apply_action(state, 1, {"action": "timeout"})
    assert state["phase"] == "round_result"


def test_scribble_hint_reveals_letters_as_guess_timer_expires() -> None:
    assert progressive_hint("cat", 130, now=100) == "_ _ _"
    assert progressive_hint("cat", 115, now=100) == "C _ _"
    assert progressive_hint("cat", 100, now=100) == "C A T"


def test_play_again_resets_the_board_but_keeps_scores() -> None:
    state = new_state("scribble", player_count=2, bot_players=(1,))
    state["winner"] = 0
    state["scores"] = [250, 175]
    state["strokes"] = [{"points": [{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2}], "color": "#315542", "size": 5}]
    updated = apply_action(state, 0, {"action": "play_again"})
    assert updated["winner"] is None
    assert updated["phase"] == "choosing"
    assert updated["strokes"] == []
    assert updated["scores"] == [250, 175]


def test_checkers_play_again_requires_a_result_and_resets_the_board() -> None:
    state = new_state("checkers", player_count=2, bot_players=(1,))
    with pytest.raises(IllegalMove, match="Finish the current game"):
        apply_action(state, 0, {"action": "play_again"})

    state["winner"] = 0
    state["board"] = [[0 for _ in range(8)] for _ in range(8)]
    updated = apply_action(state, 0, {"action": "play_again"})

    assert updated["winner"] is None
    assert updated["draw"] is False
    assert updated["current_player"] == 0
    assert sum(piece != 0 for row in updated["board"] for piece in row) == 24


def test_bingo_marks_drawn_numbers_and_trivia_scores() -> None:
    bingo = new_state("bingo")
    number = bingo["card"][0][0]
    bingo["remaining"] = [number]
    bingo = apply_action(bingo, 0, {"action": "draw"})
    assert bingo["marked"][0][0] is True
    trivia = new_state("trivia")
    trivia = apply_action(trivia, 0, {"action": "select_clue", "category": "Science", "value": 300})
    trivia = apply_action(trivia, 0, {"answer": trivia["correct"], "response_ms": 1500})
    assert trivia["scores"][0] == 300
    assert trivia["phase"] == "bot"


def test_trivia_reveals_only_after_both_players_answer_and_advances() -> None:
    state = new_state("trivia")
    state = apply_action(state, 0, {"action": "select_clue", "category": "Science", "value": 100})
    correct = state["correct"]
    state = apply_action(state, 0, {"answer": correct, "response_ms": 3000})
    state = apply_action(state, 1, {"answer": correct, "response_ms": 4500})
    assert state["phase"] == "reveal"
    assert state["selected_answers"] == [correct, correct]
    state = apply_action(state, 0, {"action": "next"})
    assert state["phase"] == "board"
    assert state["question_index"] == 1
    assert state["selected_answers"] == [None, None]


def test_trivia_human_second_player_can_advance_reveal() -> None:
    state = new_state("trivia", bot_players=())
    state = apply_action(state, 0, {"action": "select_clue", "category": "Animals", "value": 200})
    correct = state["correct"]
    state = apply_action(state, 0, {"answer": correct})
    state = apply_action(state, 1, {"answer": correct})
    assert state["phase"] == "reveal"
    assert state["current_player"] == 1
    state = apply_action(state, 1, {"action": "next"})
    assert state["phase"] == "board"
    assert state["question_index"] == 1


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
    state = apply_action(state, 0, {"action": "select_clue", "category": "Technology", "value": 100})
    state = apply_action(state, 0, {"answer": state["correct"]})
    state = apply_action(state, 1, {"answer": state["correct"]})
    public_state = match.snapshot()["state"]
    assert "correct" not in public_state
    assert public_state["correct_answer"] == state["correct"]


def test_trivia_board_uses_all_fifteen_clues_and_selects_a_winner() -> None:
    state = new_state("trivia")
    for index in range(15):
        if state["phase"] == "board":
            category = state["categories"][index % len(state["categories"])]
            value = next(value for value in state["point_values"] if f"{category}:{value}" not in state["used_clues"])
            state = apply_action(state, state["current_player"], {"action": "select_clue", "category": category, "value": value})
        correct = state["correct"]
        state = apply_action(state, 0, {"answer": correct})
        state = apply_action(state, 1, {"answer": (correct + 1) % 4})
        state = apply_action(state, 0, {"action": "next"})
        if index < 4:
            assert state["question_index"] == index + 1
    assert state["phase"] == "complete"
    assert state["winner"] == 0
    assert state["draw"] is False
