from datetime import date, timedelta

from app.routes.api import daily_checkin_question


def test_checkin_prompt_changes_each_day_of_the_week() -> None:
    sunday = date(2026, 8, 16)
    prompts = [daily_checkin_question(sunday + timedelta(days=offset)) for offset in range(7)]

    assert len(set(prompts)) == 7
    assert daily_checkin_question(sunday) != daily_checkin_question(sunday + timedelta(days=1))
