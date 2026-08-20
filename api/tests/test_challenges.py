from datetime import date

from app.routes.api import CHALLENGE_TEMPLATES, challenge_window


def test_challenge_window_runs_monday_through_sunday() -> None:
    start, end = challenge_window(date(2026, 8, 13))

    assert start == date(2026, 8, 10)
    assert end == date(2026, 8, 16)


def test_weekly_challenges_are_safe_and_have_unique_slugs() -> None:
    slugs = [str(template["slug"]) for template in CHALLENGE_TEMPLATES]

    assert len(slugs) == 5
    assert len(set(slugs)) == len(slugs)
    assert all(1 <= int(template["xp"]) <= 100 for template in CHALLENGE_TEMPLATES)
