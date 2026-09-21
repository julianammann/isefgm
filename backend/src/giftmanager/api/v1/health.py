from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from giftmanager.core.db import SessionDep
from giftmanager.schemas.health import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", operation_id="healthLive")
async def live() -> HealthOut:
    return HealthOut(status="ok", database=False)


@router.get("/ready", operation_id="healthReady")
async def ready(session: SessionDep) -> HealthOut:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError, OSError:
        return HealthOut(status="degraded", database=False)
    return HealthOut(status="ok", database=True)
