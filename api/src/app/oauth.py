import asyncio
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token

from app.config import Settings

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str
    picture: str | None


def google_oauth_configured(settings: Settings) -> bool:
    return settings.google_oauth_enabled and bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_redirect_uri
    )


def _state_key(settings: Settings) -> bytes:
    secret = settings.google_oauth_client_secret
    if not secret:
        raise GoogleOAuthError("Google sign-in is not configured")
    return hashlib.sha256(f"safe-space-google-state:{secret}".encode()).digest()


def create_oauth_state(settings: Settings) -> tuple[str, str, str]:
    import secrets

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    payload = json.dumps(
        {
            "state": state,
            "nonce": nonce,
            "exp": int(time.time()) + settings.google_oauth_state_ttl_seconds,
        },
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(_state_key(settings), encoded.encode(), hashlib.sha256).hexdigest()
    return state, nonce, f"{encoded}.{signature}"


def verify_oauth_state(settings: Settings, cookie: str | None, returned_state: str | None) -> str:
    if not cookie or not returned_state:
        raise GoogleOAuthError("Missing OAuth state")
    try:
        encoded, signature = cookie.rsplit(".", 1)
        expected = hmac.new(_state_key(settings), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise GoogleOAuthError("Invalid OAuth state signature")
        padding = "=" * (-len(encoded) % 4)
        payload = cast(dict[str, Any], json.loads(base64.urlsafe_b64decode(encoded + padding)))
        if int(payload["exp"]) < int(time.time()):
            raise GoogleOAuthError("Expired OAuth state")
        if not hmac.compare_digest(str(payload["state"]), returned_state):
            raise GoogleOAuthError("OAuth state mismatch")
        nonce = str(payload["nonce"])
        if not nonce:
            raise GoogleOAuthError("Missing OAuth nonce")
        return nonce
    except GoogleOAuthError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise GoogleOAuthError("Malformed OAuth state") from exc


def build_google_authorize_url(settings: Settings, state: str, nonce: str) -> str:
    if not google_oauth_configured(settings):
        raise GoogleOAuthError("Google sign-in is not configured")
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode({
        'client_id': settings.google_oauth_client_id,
        'redirect_uri': settings.google_oauth_redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'nonce': nonce,
        'prompt': 'select_account',
    })}"


def frontend_oauth_redirect(settings: Settings, error: str | None = None) -> str:
    redirect_uri = settings.google_oauth_redirect_uri or ""
    parsed = urlsplit(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GoogleOAuthError("Google redirect URI is invalid")
    path = "/login" if error else "/"
    query = urlencode({"oauth_error": error}) if error else ""
    return f"{parsed.scheme}://{parsed.netloc}{path}{f'?{query}' if query else ''}"


def _exchange_code(settings: Settings, code: str) -> str:
    data = urlencode(
        {
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    request = Request(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = cast(dict[str, Any], json.load(response))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GoogleOAuthError("Google token exchange failed") from exc
    token = payload.get("id_token")
    if not isinstance(token, str) or not token:
        raise GoogleOAuthError("Google did not return an ID token")
    return token


def identity_from_claims(claims: dict[str, Any], nonce: str) -> GoogleIdentity:
    if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise GoogleOAuthError("Google nonce mismatch")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleOAuthError("Google email is not verified")
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(email, str) or not email:
        raise GoogleOAuthError("Google identity is incomplete")
    name_claim = claims.get("name")
    name = name_claim.strip() if isinstance(name_claim, str) else ""
    picture_claim = claims.get("picture")
    picture = (
        picture_claim
        if isinstance(picture_claim, str) and picture_claim.startswith("https://")
        else None
    )
    return GoogleIdentity(
        subject=subject,
        email=email.strip().lower(),
        name=name or email.split("@", 1)[0],
        picture=picture,
    )


def _verify_id_token(settings: Settings, token: str, nonce: str) -> GoogleIdentity:
    try:
        claims = id_token.verify_oauth2_token(
            token,
            GoogleAuthRequest(),
            settings.google_oauth_client_id,
        )  # type: ignore[no-untyped-call]
    except (GoogleAuthError, ValueError, TypeError) as exc:
        raise GoogleOAuthError("Google ID token validation failed") from exc
    return identity_from_claims(cast(dict[str, Any], claims), nonce)


async def exchange_google_code(
    settings: Settings, code: str, nonce: str
) -> GoogleIdentity:
    token = await asyncio.to_thread(_exchange_code, settings, code)
    return await asyncio.to_thread(_verify_id_token, settings, token, nonce)
