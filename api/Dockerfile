FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src

EXPOSE 10000

FROM base AS runtime
CMD ["sh", "-c", ".venv/bin/alembic upgrade head && exec .venv/bin/uvicorn app.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-10000}"]

FROM base AS test
RUN uv sync --frozen
CMD [".venv/bin/pytest"]
