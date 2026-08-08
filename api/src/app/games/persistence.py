from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GameEvent, GameMatch, GameMatchPlayer


async def create_persisted_match(
    db: AsyncSession,
    match_id: str,
    room_id: int,
    game_type: str,
    player_user_id: int,
    state: dict[str, Any],
    seats: list[dict[str, Any]] | None = None,
) -> GameMatch:
    match = GameMatch(
        id=match_id,
        room_id=room_id,
        game_type=game_type,
        player_user_id=player_user_id,
        state=state,
        version=0,
    )
    db.add(match)
    await db.flush()
    for seat in seats or [
        {"seat_index": 0, "user_id": player_user_id, "player_type": "human", "display_name": "You"}
    ]:
        db.add(GameMatchPlayer(match_id=match_id, **seat))
    await db.flush()
    return match


async def record_state(
    db: AsyncSession,
    match: GameMatch,
    actor_user_id: int | None,
    action: dict[str, Any],
    state: dict[str, Any],
) -> GameEvent:
    stored = await db.scalar(select(GameMatch).where(GameMatch.id == match.id).with_for_update())
    if stored is None:
        raise ValueError("Persisted match not found")
    stored.version += 1
    stored.state = state
    if state.get("winner") is not None:
        stored.status = "completed"
    event = GameEvent(
        match_id=stored.id,
        sequence=stored.version,
        actor_user_id=actor_user_id,
        action=action,
        state=state,
    )
    db.add(event)
    await db.flush()
    return event
