from datetime import date, timedelta

from app.routes.api import current_checkin_streak


def test_current_checkin_streak_counts_consecutive_days() -> None:
    today = date(2026, 8, 6)
    assert (
        current_checkin_streak([today, today - timedelta(days=1), today - timedelta(days=2)], today)
        == 3
    )


def test_current_checkin_streak_allows_yesterday_but_expires_after_a_gap() -> None:
    today = date(2026, 8, 6)
    assert current_checkin_streak([today - timedelta(days=1)], today) == 1
    assert current_checkin_streak([today - timedelta(days=2)], today) == 0
