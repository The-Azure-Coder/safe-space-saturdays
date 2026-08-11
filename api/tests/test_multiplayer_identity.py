import pytest

from app.games.universal import UniversalMatchManager


@pytest.mark.parametrize("game_type", ["ludo", "dominoes", "trivia", "scribble"])
def test_multiplayer_snapshots_keep_fixed_player_names_and_viewer_seats(game_type: str) -> None:
    manager = UniversalMatchManager()
    match = manager.create(
        room_id=9,
        user_id=101,
        game_type=game_type,
        player_count=2,
        player_ids={101: 0, 202: 1},
        bot_players=(),
        player_names={0: "Host", 1: "Hugo"},
    )

    host_state = match.snapshot(101)["state"]
    guest_state = match.snapshot(202)["state"]

    assert host_state["seat_index"] == 0
    assert guest_state["seat_index"] == 1
    assert [player["name"] for player in guest_state["players"]] == ["Host", "Hugo"]
    assert [player["is_bot"] for player in guest_state["players"]] == [False, False]

    if game_type == "dominoes":
        assert host_state["hands"][0]
        assert host_state["hands"][1] == []
        assert guest_state["hands"][0] == []
        assert guest_state["hands"][1]
    if game_type == "scribble":
        assert host_state["is_drawer"] is True
        assert guest_state["is_drawer"] is False
        assert guest_state["drawer_name"] == "Host"


def test_bingo_snapshot_returns_only_the_viewers_card() -> None:
    manager = UniversalMatchManager()
    match = manager.create(
        room_id=10,
        user_id=101,
        game_type="bingo",
        player_count=2,
        player_ids={101: 0, 202: 1},
        bot_players=(),
    )

    host_state = match.snapshot(101)["state"]
    guest_state = match.snapshot(202)["state"]

    assert host_state["seat_index"] == 0
    assert guest_state["seat_index"] == 1
    assert host_state["card"]
    assert guest_state["card"]
    assert "cards" not in host_state
    assert "cards" not in guest_state
