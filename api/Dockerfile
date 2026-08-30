FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src

EXPOSE 10000
CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn app.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-10000}"]
