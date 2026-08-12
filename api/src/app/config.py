import socket
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    api_cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    session_cookie_name: str = "safe_space_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False
    upload_dir: Path = DEFAULT_UPLOAD_DIR
    max_upload_bytes: int = 10_000_000
    redis_url: str = "redis://localhost:6379/0"
    realtime_node_id: str = socket.gethostname()
    use_cloudinary: bool = False
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    google_oauth_enabled: bool = False
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
    google_oauth_state_ttl_seconds: int = 600

    @model_validator(mode="after")
    def require_secure_production_cookies(self) -> "Settings":
        if self.database_url.startswith("postgres://"):
            self.database_url = "postgresql+psycopg://" + self.database_url.removeprefix(
                "postgres://"
            )
        elif self.database_url.startswith("postgresql://"):
            self.database_url = "postgresql+psycopg://" + self.database_url.removeprefix(
                "postgresql://"
            )
        if self.app_env == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true when APP_ENV=production")
        if self.google_oauth_enabled and not all(
            (
                self.google_oauth_client_id,
                self.google_oauth_client_secret,
                self.google_oauth_redirect_uri,
            )
        ):
            raise ValueError(
                "GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and "
                "GOOGLE_OAUTH_REDIRECT_URI are required when GOOGLE_OAUTH_ENABLED=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
