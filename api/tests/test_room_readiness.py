from app.models import GameRoom, RoomParticipant
from app.routes.api import room_participant_is_ready


def test_host_is_always_ready_even_with_stale_participant_state() -> None:
    room = GameRoom(id=7, game_id=1, host_id=11, name="Connect Four", max_players=2)
    host = RoomParticipant(room_id=7, user_id=11, seat_index=0, ready=False)

    assert room_participant_is_ready(room, host) is True


def test_non_host_still_controls_their_own_readiness() -> None:
    room = GameRoom(id=7, game_id=1, host_id=11, name="Connect Four", max_players=2)
    guest = RoomParticipant(room_id=7, user_id=12, seat_index=1, ready=False)

    assert room_participant_is_ready(room, guest) is False
    guest.ready = True
    assert room_participant_is_ready(room, guest) is True
