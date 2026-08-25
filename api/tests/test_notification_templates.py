from datetime import date

from app.notification_templates import weekly_performers_email


def test_weekly_podium_email_includes_date_window_and_profile_images() -> None:
    html, text = weekly_performers_email(
        winners=[
            (1, "First Player", 300, "https://cdn.example/first.png"),
            (2, "Second Player", 200, None),
            (3, "Third Player", 100, "https://cdn.example/third.png"),
        ],
        period_start=date(2026, 8, 15),
        period_end=date(2026, 8, 22),
        action_url="https://safe-space.example/leaderboard",
    )

    assert "August 15" in html
    assert "August 22" in html
    assert 'src="https://cdn.example/first.png"' in html
    assert 'src="https://cdn.example/third.png"' in html
    assert "First Player" in text
    assert "2026-08-15 through 2026-08-22" in text
