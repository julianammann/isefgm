"""Scheduler run: plan, clean up and send notifications (F-13, QZ-05)."""

import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.clock import Clock
from giftmanager.core.mail import Mailer
from giftmanager.services.notification import (
    PlannedMail,
    dispatch_due,
    expire,
    fail_stuck,
    plan,
)

logger = logging.getLogger(__name__)

Planner = Callable[[AsyncSession, datetime], Awaitable[list[PlannedMail]]]

# Each notification type registers its `due` function here.
PLANNERS: list[Planner] = []


async def run_once(
    *,
    clock: Clock,
    sessionmaker: async_sessionmaker[AsyncSession],
    mailer: Mailer,
    planners: Sequence[Planner] = PLANNERS,
) -> int:
    """Expire and fail stale rows, plan every type, send what is due; returns mails sent.

    A failing planner is logged and does not stop the others or the sending.
    """
    now = clock.now()
    async with sessionmaker() as session, session.begin():
        await expire(session, now)
        await fail_stuck(session, now)
    for planner in planners:
        try:
            async with sessionmaker() as session, session.begin():
                await plan(session, await planner(session, now))
        except Exception:
            logger.exception("Planner %s failed", getattr(planner, "__name__", planner))
    return await dispatch_due(sessionmaker, mailer, clock)
