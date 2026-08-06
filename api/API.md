# Safe Space Saturdays API

The API is FastAPI-based and exposes OpenAPI documentation at `/docs` and `/redoc` while running locally at `http://localhost:8000`.

## Authentication

`POST /api/auth/register` and `POST /api/auth/login` set an HTTP-only `safe_space_session` cookie. Browser clients should send requests with credentials enabled. `POST /api/auth/logout` clears the session. Protected endpoints return `401` when no valid session is present.

## Endpoints

| Area | Method | Path | Purpose |
| --- | --- | --- | --- |
| Health | GET | `/health/live` | Process liveness |
| Health | GET | `/health/ready` | PostgreSQL readiness |
| Auth | POST | `/api/auth/register` | Create an account |
| Auth | POST | `/api/auth/login` | Start a session |
| Auth | POST | `/api/auth/logout` | End the current session |
| Auth | GET | `/api/auth/me` | Current user |
| Auth | PATCH | `/api/auth/me` | Update display name |
| Dashboard | GET | `/api/dashboard` | Progress, rank, quote, latest check-in |
| Check-ins | GET | `/api/check-ins` | Private check-in history |
| Check-ins | POST | `/api/check-ins` | Save a completed check-in |
| Quotes | GET | `/api/quotes?category=...` | List/filter quotes |
| Quotes | POST | `/api/quotes/{id}/save` | Toggle a saved quote |
| Community | GET | `/api/community/posts` | List visible posts |
| Community | POST | `/api/community/posts` | Create a post |
| Community | POST | `/api/community/posts/with-image` | Create a post with a JPEG, PNG, or WebP image (maximum 5 MB) |
| Community | POST | `/api/community/posts/{id}/reactions` | Toggle or change a `like`, `dislike`, or `love` reaction |
| Community | POST | `/api/community/posts/{id}/comments` | Add a comment |
| Games | GET | `/api/games` | Featured games |
| Games | GET | `/api/games/rooms` | Open rooms |
| Games | POST | `/api/games/rooms` | Create a room |
| Games | POST | `/api/games/rooms/{id}/join` | Join a room |
| Games | GET | `/api/games/winners` | Recent winners |
| Leaderboard | GET | `/api/leaderboard?period=week` | Ranked members |

All request bodies and response bodies are typed and visible in the generated OpenAPI schema. Validation errors use FastAPI's standard `422` response; missing authentication uses `401`; missing resources use `404`; duplicate or full resources use `409`.

## Local setup

```bash
cd apps/safe-space-saturdays
cp .env.example .env
docker compose up -d db
cd api
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir src --reload
```

The initial migration seeds the supplied quote and game data. Production deployments should set a strong database password, `COOKIE_SECURE=true`, and a narrow `API_CORS_ORIGINS` value.
