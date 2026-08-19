import asyncio
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.games.multi import apply_action, new_state
from app.games.universal import UniversalMatch, UniversalMatchManager
from app.models import GameMatch, GameProgress, User
from app.models.base import Base
from app.routes import api as api_routes
from app.routes.api import (
    apply_progress_to_live_match,
    grant_community_post_reward,
    grant_completed_game_rewards,
    record_game_progress_result,
    settle_completed_match_progress,
)


class FakeRewardDb:
    def __init__(self, users: dict[int, User]) -> None:
        self.users = users
        self.ledger: list[object] = []

    async def scalar(self, _: object) -> None:
        return None

    async def get(self, _: type[User], user_id: int) -> User | None:
        return self.users.get(user_id)

    def add(self, value: object) -> None:
        self.ledger.append(value)


class AsyncSessionAdapter:
    """Exercise async reward code against a real SQLAlchemy database session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def scalar(self, statement: object) -> Any:
        return self.session.scalar(statement)  # type: ignore[arg-type]

    async def get(self, model: type[object], identity: object) -> Any:
        return self.session.get(model, identity)

    def add(self, value: object) -> None:
        self.session.add(value)


@pytest.mark.asyncio
async def test_completed_game_rewards_every_human_and_maps_winner_seat() -> None:
    winner = User(id=11, xp=20, level=1)
    participant = User(id=22, xp=20, level=1)
    db = FakeRewardDb({11: winner, 22: participant})

    await grant_completed_game_rewards(db, {22: 0, 11: 1}, "match-1", 1)

    assert winner.xp == 35
    assert participant.xp == 25
    assert len(db.ledger) == 3


@pytest.mark.asyncio
async def test_first_checkers_win_creates_numeric_progress_in_database() -> None:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            User(
                id=7,
                name="First Winner",
                email="first-winner@example.com",
                password_hash="not-used-in-test",
                xp=0,
                streak=0,
                level=1,
            )
        )
        session.add(
            GameMatch(
                id="first-checkers-win",
                room_id=1,
                game_type="checkers",
                player_user_id=7,
                state={"winner": 0},
                version=1,
                status="completed",
            )
        )
        session.commit()

        await grant_completed_game_rewards(
            AsyncSessionAdapter(session),  # type: ignore[arg-type]
            {7: 0},
            "first-checkers-win",
            0,
        )
        session.flush()

        progress = session.scalar(
            sa.select(GameProgress).where(
                GameProgress.user_id == 7,
                GameProgress.game_type == "checkers",
            )
        )
        assert progress is not None
        assert progress.wins == 1
        assert progress.current_streak == 1
        assert progress.best_streak == 1
        assert progress.level == 2


@pytest.mark.asyncio
async def test_community_post_reward_awards_five_xp() -> None:
    user = User(id=7, xp=245, level=1)
    db = FakeRewardDb({7: user})

    awarded = await grant_community_post_reward(db, user.id, 42)

    assert awarded is True
    assert user.xp == 250
    assert user.level == 2


def test_two_checkers_wins_update_level_and_streak_through_play_again() -> None:
    progress = GameProgress(
        user_id=7,
        game_type="checkers",
        wins=0,
        current_streak=0,
        best_streak=0,
        level=1,
    )
    record_game_progress_result(progress, won=True)
    record_game_progress_result(progress, won=True)

    state = new_state("checkers", player_count=2, bot_players=(1,))
    state["winner"] = 0
    match = UniversalMatch(
        id="checkers-match",
        room_id=1,
        game_type="checkers",
        state=state,
        player_ids={7: 0},
    )
    apply_progress_to_live_match(match, 7, {7: progress})
    replayed = apply_action(match.state, 0, {"action": "play_again"})

    assert progress.wins == 2
    assert progress.current_streak == 2
    assert progress.best_streak == 2
    assert replayed["game_level"] == 3
    assert replayed["game_streak"] == 2
    assert replayed["bot_difficulty"] == "thoughtful"


@pytest.mark.asyncio
async def test_checkers_play_again_opens_the_next_round_for_progression() -> None:
    state = new_state("checkers", player_count=2, bot_players=(1,))
    state["winner"] = 0
    match = UniversalMatch(
        id="checkers-replay",
        room_id=1,
        game_type="checkers",
        state=state,
        player_ids={7: 0},
        reward_granted=True,
    )

    await UniversalMatchManager().action(match, 7, {"action": "play_again"})

    assert match.reward_granted is False
    assert match.state["winner"] is None


@pytest.mark.asyncio
async def test_fast_checkers_replay_waits_for_progress_settlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress = GameProgress(
        user_id=7,
        game_type="checkers",
        wins=1,
        current_streak=1,
        best_streak=1,
        level=2,
    )
    state = new_state("checkers", player_count=2, bot_players=(1,))
    state["winner"] = 0
    match = UniversalMatch(
        id="checkers-fast-replay",
        room_id=1,
        game_type="checkers",
        state=state,
        player_ids={7: 0},
    )
    settlement_started = asyncio.Event()
    release_settlement = asyncio.Event()

    async def delayed_rewards(*_args: object) -> dict[int, GameProgress]:
        settlement_started.set()
        await release_settlement.wait()
        return {7: progress}

    monkeypatch.setattr(api_routes, "grant_completed_game_rewards", delayed_rewards)
    websocket_settlement = asyncio.create_task(
        settle_completed_match_progress(object(), match, 7)  # type: ignore[arg-type]
    )
    await settlement_started.wait()

    async def replay_immediately() -> None:
        await settle_completed_match_progress(object(), match, 7)  # type: ignore[arg-type]
        await UniversalMatchManager().action(match, 7, {"action": "play_again"})

    replay = asyncio.create_task(replay_immediately())
    await asyncio.sleep(0)
    assert replay.done() is False

    release_settlement.set()
    await asyncio.gather(websocket_settlement, replay)

    assert match.state["winner"] is None
    assert match.state["game_level"] == 2
    assert match.state["game_streak"] == 1
    assert match.reward_granted is False
