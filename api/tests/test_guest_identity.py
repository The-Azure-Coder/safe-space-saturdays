from app.routes.api import new_guest_email
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
