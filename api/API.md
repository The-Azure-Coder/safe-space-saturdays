# Safe Space Saturdays API

The API is FastAPI-based and exposes OpenAPI documentation at `/docs` and `/redoc` while running locally at `http://localhost:8000`.

## Authentication

`POST /api/auth/register` and `POST /api/auth/login` set an HTTP-only `safe_space_session` cookie and return an `access_token` for native clients. Browser clients should send requests with credentials enabled. Native clients should send `Authorization: Bearer <access_token>`, store the token in platform secure storage, and use `POST /api/auth/refresh` to rotate it. `POST /api/auth/logout` accepts either the cookie or bearer token. Protected endpoints return `401` when no valid session is present.

Game WebSockets accept the same bearer token through the `Authorization` header, which allows native multiplayer clients to reconnect without browser cookies.

Google sign-in uses the server-side OpenID Connect authorization-code flow. `GET /api/auth/google/start` creates signed, short-lived `state` and `nonce` values before redirecting to Google. The callback validates those values and Google's signed ID token, links an existing account only by a verified email, and then creates the same HTTP-only session used by password login. The Google access and ID tokens are never sent to the browser or stored by the application.

## Endpoints

| Area | Method | Path | Purpose |
| --- | --- | --- | --- |
| Health | GET | `/health/live` | Process liveness |
| Health | GET | `/health/ready` | PostgreSQL readiness |
| Auth | POST | `/api/auth/register` | Create an account |
| Auth | POST | `/api/auth/login` | Start a session |
| Auth | POST | `/api/auth/refresh` | Rotate a native or browser session token |
| Auth | GET | `/api/auth/google/status` | Report whether Google sign-in is configured |
| Auth | GET | `/api/auth/google/start` | Start Google OpenID Connect sign-in |
| Auth | GET | `/api/auth/google/callback` | Validate Google identity and start a session |
| Auth | POST | `/api/auth/logout` | End the current session |
| Auth | GET | `/api/auth/me` | Current user |
| Auth | PATCH | `/api/auth/me` | Update display name |
| Auth | POST | `/api/auth/me/avatar` | Save a JPEG, PNG, or WebP profile picture; source images up to 40 MB are resized to the 10 MB output limit |
| Dashboard | GET | `/api/dashboard` | Progress, rank, quote, latest check-in |
| Check-ins | GET | `/api/check-ins?page=1&limit=20` | Private check-in history with pagination |
| Check-ins | POST | `/api/check-ins` | Save a completed check-in |
| Challenges | GET | `/api/challenges/current` | Current weekly challenges and the member's completion state |
| Challenges | GET | `/api/challenges/history?page=1&limit=10` | Completed challenge history for the current member |
| Challenges | POST | `/api/challenges/{id}/complete` | Complete one active challenge once and award its server-calculated XP |
| Quotes | GET | `/api/quotes?category=...&page=1&limit=20` | List/filter quotes with pagination |
| Quotes | POST | `/api/quotes/{id}/save` | Toggle a saved quote |
| Community | GET | `/api/community/posts?page=1&limit=20` | List visible posts with pagination and replies |
| Community | GET | `/api/community/activity/liked?page=1&limit=10` | Posts the current member liked or loved |
| Community | GET | `/api/community/activity/replied?page=1&limit=10` | Posts the current member replied to |
| Community | POST | `/api/community/posts` | Create a post |
| Community | POST | `/api/community/posts/with-image` | Create a post with a JPEG, PNG, or WebP image; source images up to 40 MB are resized to the 10 MB output limit |
| Community | POST | `/api/community/posts/{id}/reactions` | Toggle or change a `like`, `dislike`, or `love` reaction |
| Community | POST | `/api/community/posts/{id}/comments` | Add a comment |
| Games | GET | `/api/games?page=1&limit=20` | Featured games with pagination |
| Games | GET | `/api/games/rooms?page=1&limit=10` | Open rooms with pagination |
| Games | POST | `/api/games/rooms` | Create a room |
| Games | POST | `/api/games/rooms/{id}/join` | Join a room |
| Games | GET | `/api/games/winners?page=1&limit=10` | Recent winners with pagination |
| Leaderboard | GET | `/api/leaderboard?period=day&page=1&limit=10` | Ranked members for `day`, `week`, `month`, or `all` with pagination |

All request bodies and response bodies are typed and visible in the generated OpenAPI schema. Validation errors use FastAPI's standard `422` response; missing authentication uses `401`; missing resources use `404`; duplicate or full resources use `409`.

Challenges are self-attested wellbeing prompts. They never require a public post, photo, location, or private journal disclosure. Each approved member can complete a challenge once per weekly window; the database uniqueness constraint makes retries idempotent, and the API—not the browser—determines the XP award. Guest accounts cannot earn challenge XP.

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

To enable Google sign-in, configure `GOOGLE_OAUTH_ENABLED=true`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REDIRECT_URI`. The redirect URI must exactly match the authorized URI in Google Cloud. For this deployment it should use the public web origin (for example, `https://safe-space-saturdays-web.onrender.com/api/auth/google/callback`) so mobile browsers receive the session cookie as first-party.
# Games

The games foundation provides an authoritative Connect Four match with a friendly or thoughtful bot. The room must be joined before starting a match.

```text
POST /api/games/matches
{ "room_id": 12, "with_bot": true, "bot_difficulty": "friendly" }

GET  /api/games/matches/{match_id}
POST /api/games/matches/{match_id}/moves
{ "column": 3 }

WS   /api/games/matches/{match_id}/ws
{ "type": "move", "column": 3 }
```

The server owns the board, turn, legal move validation, bot move, winner, and XP reward. A human win grants 50 XP once; clients cannot submit board state, scores, or rewards. Connect Four follows the classic 7-column, 6-row, four-in-a-row rules.

The remaining session games use the same authenticated REST/WS transport:

```text
POST /api/games/sessions
{ "room_id": 12 }

POST /api/games/sessions/{match_id}/actions
{ "action": { "token": 0 } }                    # Ludo
{ "action": { "tile_index": 2, "side": "right" } } # Dominoes
{ "action": { "action": "draw" } }             # Bingo
{ "action": { "answer": 1 } }                  # Trivia
```

Ludo uses exact-home movement and six-to-leave-base rules; Dominoes uses a double-six block line with pass/block resolution; Bingo uses a server-drawn 75-ball card with a free centre and line claim; Trivia uses five multiple-choice questions with server-side scoring. PostgreSQL stores snapshots, events, and rewards, while Redis distributes live state updates between API replicas. If Redis is unavailable, the local WebSocket still works.
