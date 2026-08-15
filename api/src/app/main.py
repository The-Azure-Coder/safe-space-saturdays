from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

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


app = FastAPI(
    title="Safe Space Saturdays API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def is_same_origin_proxy_request(request: Request, origin: str) -> bool:
    """Allow the mono-service proxy's public origin without stale env config."""
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    if not forwarded_host or forwarded_proto not in {"http", "https"}:
        return False
    return origin == f"{forwarded_proto}://{forwarded_host}"


@app.middleware("http")
async def security_headers_and_origin_check(request: Request, call_next):
    has_session = request.cookies.get(settings.session_cookie_name)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and has_session:
        origin = request.headers.get("origin")
        if origin and origin not in settings.api_cors_origins and not is_same_origin_proxy_request(request, origin):
            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.app_env == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


app.include_router(health_router)
app.include_router(api_router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
