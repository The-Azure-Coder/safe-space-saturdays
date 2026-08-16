from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import get_session
from app.main import app
from app.oauth import (
    GoogleIdentity,
    GoogleOAuthError,
    build_google_authorize_url,
    create_oauth_state,
    frontend_oauth_redirect,
    identity_from_claims,
    verify_oauth_state,
)
from app.routes import api as api_routes


def oauth_settings() -> Settings:
    return Settings(
        _env_file=None,
        google_oauth_enabled=True,
        google_oauth_client_id="client.apps.googleusercontent.com",
        google_oauth_client_secret="test-secret",
        google_oauth_redirect_uri="https://safe-space.example/api/auth/google/callback",
    )


def test_signed_oauth_state_round_trip_and_tamper_rejection() -> None:
    settings = oauth_settings()
    state, nonce, cookie = create_oauth_state(settings)

    assert verify_oauth_state(settings, cookie, state) == nonce

    with pytest.raises(GoogleOAuthError):
        verify_oauth_state(settings, f"{cookie}changed", state)
    with pytest.raises(GoogleOAuthError):
        verify_oauth_state(settings, cookie, "wrong-state")


def test_google_authorize_url_uses_server_flow_security_parameters() -> None:
    settings = oauth_settings()
    target = urlsplit(build_google_authorize_url(settings, "state-value", "nonce-value"))
    query = parse_qs(target.query)

    assert target.scheme == "https"
    assert target.netloc == "accounts.google.com"
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["state"] == ["state-value"]
    assert query["nonce"] == ["nonce-value"]
    assert query["redirect_uri"] == [settings.google_oauth_redirect_uri]


def test_verified_claims_create_normalized_identity() -> None:
    identity = identity_from_claims(
        {
            "sub": "google-user-123",
            "email": " Person@Example.com ",
            "email_verified": True,
            "name": "  Person Name  ",
            "picture": "https://images.example/avatar.png",
            "nonce": "expected-nonce",
        },
        "expected-nonce",
    )

    assert identity.subject == "google-user-123"
    assert identity.email == "person@example.com"
    assert identity.name == "Person Name"
    assert identity.picture == "https://images.example/avatar.png"


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "1", "email": "a@example.com", "email_verified": False, "nonce": "n"},
        {"sub": "1", "email": "a@example.com", "email_verified": True, "nonce": "wrong"},
        {"sub": "", "email": "a@example.com", "email_verified": True, "nonce": "n"},
    ],
)
def test_untrusted_google_claims_are_rejected(claims: dict[str, object]) -> None:
    with pytest.raises(GoogleOAuthError):
        identity_from_claims(claims, "n")


def test_callback_redirect_stays_on_configured_web_origin() -> None:
    settings = oauth_settings()

    assert frontend_oauth_redirect(settings) == "https://safe-space.example/"
    assert (
        frontend_oauth_redirect(settings, "failed")
        == "https://safe-space.example/login?oauth_error=failed"
    )


def test_start_endpoint_sets_short_lived_http_only_state_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = oauth_settings()
    monkeypatch.setattr(api_routes, "get_settings", lambda: settings)

    with TestClient(app) as client:
        response = client.get("/api/auth/google/start", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/")
    cookie = response.headers["set-cookie"]
    assert "safe_space_google_oauth=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/api/auth/google" in cookie


class FakeOAuthSession:
    def __init__(self) -> None:
        self.scalar_results: list[object | None] = [None, None, 0]
        self.added: list[object] = []

    async def scalar(self, _: object) -> object | None:
        return self.scalar_results.pop(0)

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.added[0].id = 42  # type: ignore[attr-defined]

    async def commit(self) -> None:
        return None


def test_callback_creates_local_session_from_verified_google_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = oauth_settings()
    state, _, cookie = create_oauth_state(settings)
    session = FakeOAuthSession()

    async def verified_identity(*_: object) -> GoogleIdentity:
        return GoogleIdentity(
            subject="google-42",
            email="member@example.com",
            name="Member",
            picture="https://images.example/member.png",
        )

    async def override_session():
        yield session

    monkeypatch.setattr(api_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(api_routes, "exchange_google_code", verified_identity)
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            client.cookies.set("safe_space_google_oauth", cookie)
            response = client.get(
                "/api/auth/google/callback",
                params={"state": state, "code": "one-time-code"},
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 303
    assert response.headers["location"] == "https://safe-space.example/"
    assert any("safe_space_session=" in value for value in response.headers.get_list("set-cookie"))
    created_user = session.added[0]
    assert created_user.google_subject == "google-42"  # type: ignore[attr-defined]
