"""Liveness and readiness probes for container healthchecks."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from giftmanager.core.db import SessionDep
from giftmanager.schemas.health import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    operation_id="healthLive",
    summary="Process is up",
    description="Answers as soon as the process accepts requests; does not touch the database. "
    "Target of the container healthcheck.",
)
async def live() -> HealthOut:
    """Report that the process accepts requests, without touching the database."""
    return HealthOut(status="ok", database=False)


@router.get(
    "/ready",
    operation_id="healthReady",
    summary="Database reachable",
    description="Runs `SELECT 1`. Without a database it returns `status: degraded` with HTTP 200, "
    "so that Traefik keeps the container in rotation while it is still starting.",
)
async def ready(session: SessionDep) -> HealthOut:
    """Report whether the database answers `SELECT 1`.

    Returns `degraded` with HTTP 200 instead of an error, so the container stays in
    rotation while the database is still starting.
    """
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError, OSError:
        return HealthOut(status="degraded", database=False)
    return HealthOut(status="ok", database=True)
