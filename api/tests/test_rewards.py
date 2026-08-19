import pytest

from app.games.multi import apply_action, new_state
from app.games.universal import UniversalMatch
from app.models import GameProgress, User
from app.routes.api import (
    apply_progress_to_live_match,
    grant_community_post_reward,
    grant_completed_game_rewards,
    record_game_progress_result,
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
