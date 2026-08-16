import pytest

from app.models import User
from app.routes.api import grant_community_post_reward, grant_completed_game_rewards


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
