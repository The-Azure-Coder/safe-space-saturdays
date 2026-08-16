#!/bin/sh
set -eu

api_pid=''
shutdown() {
  if [ -n "$api_pid" ]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
}
trap shutdown INT TERM EXIT

cd /app/api
uv run alembic upgrade head
PORT=8000 uv run uvicorn app.main:app --app-dir src --host 127.0.0.1 --port 8000 &
api_pid=$!

echo 'Internal API is starting; the frontend readiness bridge will report warming until it is ready.'
cd /app/web
exec node server.mjs
