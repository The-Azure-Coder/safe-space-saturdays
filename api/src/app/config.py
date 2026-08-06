import socket
from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    max_upload_bytes: int = 5_000_000
    redis_url: str = "redis://localhost:6379/0"
    realtime_node_id: str = socket.gethostname()


@lru_cache
def get_settings() -> Settings:
    return Settings()
