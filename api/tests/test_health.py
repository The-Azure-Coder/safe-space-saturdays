from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app


class FakeSession:
    async def execute(self, *_: Any, **__: Any) -> None:
        return None


async def fake_session() -> AsyncIterator[FakeSession]:
    yield FakeSession()


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "api"}


def test_readiness_checks_database_dependency() -> None:
    app.dependency_overrides[get_session] = fake_session
    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
