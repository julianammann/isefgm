"""Scheduler run: plan, clean up and send notifications (F-13, QZ-05)."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import (  # pyright: ignore[reportMissingTypeStubs]
    AsyncIOScheduler,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.clock import Clock, get_clock
from giftmanager.core.config import get_settings
from giftmanager.core.db import get_sessionmaker
from giftmanager.core.logging import configure_logging
from giftmanager.core.mail import Mailer, get_mailer
from giftmanager.services import birthday_digest, season_overview
from giftmanager.services.notification import (
    PlannedMail,
    dispatch_due,
    expire,
    fail_stuck,
    plan,
)

logger = logging.getLogger(__name__)

INTERVAL = timedelta(minutes=5)
# Below INTERVAL so a hung run cannot block every later tick. It only guards against hangs: a cut
# mid-send (a hang, or one send slower than the headroom over SEND_BUDGET) leaves that one row in
# `sending`; fail_stuck marks it `failed` after 15 minutes and it is not resent (same path as
# SIGTERM). The remaining `planned` rows go out on the next run.
RUN_TIMEOUT = timedelta(minutes=4)
# Soft deadline: no new mail is claimed after this, leaving headroom for the last send.
SEND_BUDGET = timedelta(minutes=3)

Planner = Callable[[AsyncSession, datetime], Awaitable[list[PlannedMail]]]

# Each notification type registers its `due` function here.
PLANNERS: list[Planner] = [birthday_digest.due, season_overview.due]


async def run_once(
    *,
    clock: Clock,
    sessionmaker: async_sessionmaker[AsyncSession],
    mailer: Mailer,
    planners: Sequence[Planner] = PLANNERS,
) -> int:
    """Expire and fail stale rows, plan every type, send what is due; returns mails sent.

    A failing planner is logged and does not stop the others or the sending. Raises
    `TimeoutError` when the run exceeds `RUN_TIMEOUT`.
    """
    async with asyncio.timeout(RUN_TIMEOUT.total_seconds()):
        now = clock.now()
        async with sessionmaker() as session, session.begin():
            await expire(session, now)
            await fail_stuck(session, now)
        for planner in planners:
            try:
                async with sessionmaker() as session, session.begin():
                    await plan(session, await planner(session, now))
            except Exception as exc:  # noqa: BLE001  # logged by type only, see below
                # Type only: the message can carry mail contents (e.g. Postgres row DETAIL).
                logger.error(
                    "Planner %s.%s failed: %s",
                    getattr(planner, "__module__", "?"),
                    getattr(planner, "__qualname__", repr(planner)),
                    type(exc).__name__,
                )
        return await dispatch_due(sessionmaker, mailer, clock, until=now + SEND_BUDGET)


async def _serve() -> None:
    # shortcut: a deploy during a send ends the process on SIGTERM and leaves the row in
    # `sending`; fail_stuck marks it `failed` after 15 minutes and it is not resent. Upgrade if
    # that loss becomes unacceptable.
    scheduler = AsyncIOScheduler(timezone=UTC)
    scheduler.add_job(  # pyright: ignore[reportUnknownMemberType]
        run_once,
        "interval",
        seconds=INTERVAL.total_seconds(),
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=None,
        kwargs={"clock": get_clock(), "sessionmaker": get_sessionmaker(), "mailer": get_mailer()},
    )
    scheduler.start()
    await asyncio.Event().wait()


def main() -> int:
    """Run the scheduler process until it is killed."""
    settings = get_settings()
    configure_logging(settings.log_level, json=not settings.is_dev)
    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
