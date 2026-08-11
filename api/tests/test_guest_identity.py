import pytest
from fastapi import HTTPException

from app.models import User
from app.routes.api import leaderboard_me, new_guest_email, user_response
from app.schemas import UserResponse


def test_guest_email_is_valid_for_auth_response() -> None:
    email = new_guest_email()

    response = UserResponse(
        id=1,
        name="Guest Player",
        email=email,
        role="guest",
        is_approved=True,
        xp=0,
        streak=0,
        level=1,
    )

    assert str(response.email) == email
    assert email.endswith("@guests.safespacesaturdays.app")


def test_legacy_guest_email_cannot_break_user_responses() -> None:
    guest = User(
        id=42,
        name="Legacy Guest",
        email="guest-old@guest.invalid",
        password_hash="unused",
        role="guest",
        is_guest=True,
        is_approved=True,
        xp=0,
        streak=0,
        level=1,
    )

    response = user_response(guest)

    assert str(response.email) == "guest-42@guests.safespacesaturdays.app"


@pytest.mark.asyncio
async def test_temporary_guest_cannot_request_a_leaderboard_rank() -> None:
    guest = User(
        id=43,
        name="Temporary Guest",
        email="guest-test@guests.safespacesaturdays.app",
        password_hash="unused",
        role="guest",
        is_guest=True,
        is_approved=True,
        xp=10,
        streak=0,
        level=1,
    )

    with pytest.raises(HTTPException) as error:
        await leaderboard_me(user=guest, db=None, period="all")  # type: ignore[arg-type]

    assert error.value.status_code == 403
    assert error.value.detail == "Temporary guest players are not ranked"
