from collections.abc import AsyncIterator
from typing import Any

import pytest
from starlette.websockets import WebSocket

from app.games.manager import LiveMatch
from app.games.multi import new_state
from app.games.universal import UniversalMatch, universal_matches
from app.routes import api


class RecordingSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, message: dict[str, Any]) -> None:
        self.messages.append(message)


def websocket_with_origin(origin: str, forwarded_host: str = "safe-space.example") -> WebSocket:
    async def receive() -> dict[str, Any]:
        return {"type": "websocket.disconnect"}

    async def send(_message: dict[str, Any]) -> None:
        return None

    return WebSocket(
        {
            "type": "websocket",
            "path": "/api/games/sessions/test/ws",
            "headers": [
                (b"origin", origin.encode()),
                (b"x-forwarded-host", forwarded_host.encode()),
                (b"x-forwarded-proto", b"https"),
            ],
            "scheme": "wss",
            "server": ("safe-space.example", 443),
            "client": ("127.0.0.1", 1234),
            "query_string": b"",
            "root_path": "",
            "subprotocols": [],
        },
        receive,
        send,
    )


def test_websocket_origin_allows_proxy_origin_and_rejects_cross_site() -> None:
    assert api.websocket_origin_allowed(websocket_with_origin("https://safe-space.example"))
    assert not api.websocket_origin_allowed(websocket_with_origin("https://attacker.example"))


@pytest.mark.asyncio
async def test_universal_relay_applies_newer_remote_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    match = UniversalMatch(
        id="remote-match",
        room_id=1,
        game_type="abc-fast-slow",
        state={"phase": "letter_picker", "players": [{"name": "Player"}]},
        player_ids={7: 0},
        version=2,
    )
    socket = RecordingSocket()

    async def messages(_channel: str) -> AsyncIterator[dict[str, Any]]:
        yield {
            "origin": "another-node",
            "payload": {
                "type": "state",
                "version": 3,
                "state": {
                    "phase": "answering",
                    "letter": "M",
                    "players": [{"name": "Player"}],
                },
            },
        }

    monkeypatch.setattr(api.realtime_bus, "subscribe", messages)
    await api.relay_remote_universal_events(socket, match, 7)  # type: ignore[arg-type]

    assert match.version == 3
    assert match.state["letter"] == "M"
    assert socket.messages[-1]["match"]["state"]["seat_index"] == 0


def test_deadline_actions_cover_timed_universal_games() -> None:
    abc = UniversalMatch(
        id="abc",
        room_id=1,
        game_type="abc-fast-slow",
        state={"phase": "answering", "deadline": 12},
        player_ids={1: 0},
    )
    trivia = UniversalMatch(
        id="trivia",
        room_id=1,
        game_type="trivia",
        state={"phase": "question", "deadline": 13, "current_player": 1},
        player_ids={1: 0, 2: 1},
    )
    scribble = UniversalMatch(
        id="scribble",
        room_id=1,
        game_type="scribble",
        state={"phase": "guessing", "guess_deadline": 14, "current_drawer": 0},
        player_ids={1: 0, 2: 1},
    )

    assert api.universal_deadline_action(abc) == (0, {"action": "timeout"}, 12)
    assert api.universal_deadline_action(trivia) == (1, {"answer": -1}, 13)
    assert api.universal_deadline_action(scribble) == (1, {"action": "timeout"}, 14)


def test_connect_snapshot_refreshes_local_authoritative_state() -> None:
    match = LiveMatch(id="connect", room_id=1)
    snapshot = match.snapshot()
    snapshot["current_player"] = 2
    snapshot["move_count"] = 4

    api.apply_connect_snapshot(match, snapshot)

    assert match.state.current_player == 2
    assert match.state.move_count == 4


@pytest.mark.asyncio
async def test_six_player_abc_bots_finish_their_valid_ballots() -> None:
    state = new_state("abc-fast-slow", player_count=6, bot_players=(1, 2, 3, 4, 5))
    state["letter_chooser"] = 0
    state["dictator_player"] = 0
    match = UniversalMatch(
        id="six-player-abc",
        room_id=1,
        game_type="abc-fast-slow",
        state=state,
        player_ids={10: 0},
        bot_players=(1, 2, 3, 4, 5),
        bot_player=1,
    )

    await universal_matches.action(
        match, 10, {"action": "start_picker", "speed": "fast"}, broadcast=False
    )
    await universal_matches.action(match, 10, {"action": "stop_picker"}, broadcast=False)
    await universal_matches.action(
        match, 10, {"action": "submit", "answers": {}}, broadcast=False
    )

    assert match.state["phase"] == "voting"
    assert match.state["voted"][1:] == [True, True, True, True, True]
