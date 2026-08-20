from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ready"]
    service: Literal["api"] = "api"


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ready")


@router.get("/ready", response_model=HealthResponse)
async def ready(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ready")
