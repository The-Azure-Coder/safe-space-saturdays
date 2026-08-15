from datetime import UTC, datetime

import pytest

from app.routes.api import leaderboard_period_start


@pytest.mark.parametrize(
    ("period", "moment", "expected"),
    [
        ("day", datetime(2026, 8, 15, 18, 30, tzinfo=UTC), datetime(2026, 8, 15, tzinfo=UTC)),
        # Saturday belongs to the week that began on the previous Sunday.
        ("week", datetime(2026, 8, 15, 18, 30, tzinfo=UTC), datetime(2026, 8, 9, tzinfo=UTC)),
        # Sunday starts a new leaderboard week.
        ("week", datetime(2026, 8, 16, 0, 1, tzinfo=UTC), datetime(2026, 8, 16, tzinfo=UTC)),
        ("month", datetime(2026, 8, 15, 18, 30, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC)),
    ],
)
def test_leaderboard_periods_are_calendar_boundaries(period, moment, expected):
    assert leaderboard_period_start(period, moment) == expected


def test_all_time_is_not_a_window():
    with pytest.raises(ValueError):
        leaderboard_period_start("all", datetime.now(UTC))
