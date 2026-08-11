from app.models import User
from app.routes.api import new_guest_email, user_response
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
