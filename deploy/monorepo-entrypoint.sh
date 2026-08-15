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

attempt=0
until curl -fsS --max-time 3 http://127.0.0.1:8000/health/ready >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo 'The internal API did not become ready within 60 seconds.' >&2
    exit 1
  fi
  sleep 1
done

echo 'Internal API is ready; starting the frontend server.'
cd /app/web
exec node server.mjs
