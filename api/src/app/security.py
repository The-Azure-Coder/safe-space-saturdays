import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Session, User


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=actual_salt, n=2**14, r=8, p=1)
    return f"scrypt${actual_salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, digest = encoded.split("$")
        if algorithm != "scrypt":
            return False
        candidate = hash_password(password, bytes.fromhex(salt)).split("$")[-1]
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def new_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    return token, hashlib.sha256(token.encode()).hexdigest()


async def get_current_user(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization[7:]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await session.execute(
        select(User)
        .join(Session, Session.user_id == User.id)
        .where(
            Session.token_hash == token_hash,
            Session.expires_at > datetime.now(UTC),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


async def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def session_expiry(remember_me: bool) -> datetime:
    days = get_settings().session_ttl_days if remember_me else 1
    return datetime.now(UTC) + timedelta(days=days)
