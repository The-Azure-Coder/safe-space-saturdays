from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import engine
from app.games.realtime import realtime_bus
from app.routes.api import router as api_router
from app.routes.health import router as health_router

settings = get_settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await realtime_bus.close()
    await engine.dispose()


app = FastAPI(title="Safe Space Saturdays API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router)
app.include_router(api_router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
