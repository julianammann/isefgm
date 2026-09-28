"""Async SQLAlchemy engine, session factory and the per-request session dependency."""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from giftmanager.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Engine is created lazily so importing the app never touches the database."""
    return create_async_engine(str(get_settings().database_url), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the engine; loaded objects stay usable after commit."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """One transaction per request.

    Commits when the endpoint returns, rolls back when it raises. Services only
    ``flush()``; they never call ``commit()`` themselves.
    """
    async with get_sessionmaker()() as session, session.begin():
        yield session


# scope="function": commit before the response is sent. With the default "request"
# scope FastAPI runs the teardown after sending, so a failed commit would reach the
# client as a success (e.g. a session cookie for a row that was never written).
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
