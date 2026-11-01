"""Scheduler run: plan, clean up and send (F-13, QZ-05)."""

import asyncio
import functools
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from apscheduler.schedulers.asyncio import (  # pyright: ignore[reportMissingTypeStubs]
    AsyncIOScheduler,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager import scheduler
from giftmanager.core import db
from giftmanager.core.mail import Mail, MailFailure
from giftmanager.models.notification import Notification, NotificationStatus
from giftmanager.models.user import User
from giftmanager.scheduler import Planner, run_once
from giftmanager.services.notification import PlannedMail, dispatch_due
from tests.conftest import FixedClock
from tests.mail import RecordingMailer
from tests.notifications import (
    add_committed_notification,
    make_committed_user,
    planned_mail,
    reload,
)

pytestmark = pytest.mark.requirement("F-13", "QZ-05")


def due_once(user: User) -> Planner:
    async def planner(session: AsyncSession, now: datetime) -> list[PlannedMail]:
        return [
            planned_mail(
                owner_id=user.id,
                recipient=user.email,
                scheduled_for=now,
                expires_at=now + timedelta(days=1),
            )
        ]

    return planner


async def test_run_once_plans_and_sends(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    mailer = RecordingMailer()
    sent = await run_once(
        clock=clock, sessionmaker=committed_sessionmaker, mailer=mailer, planners=[due_once(user)]
    )
    assert sent == 1
    assert [m.to for m in mailer.sent] == [user.email]


async def test_run_once_twice_sends_once(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    mailer = RecordingMailer()
    for _ in range(2):
        await run_once(
            clock=clock,
            sessionmaker=committed_sessionmaker,
            mailer=mailer,
            planners=[due_once(user)],
        )
    assert len(mailer.sent) == 1


async def test_mail_outage_keeps_rows_and_does_not_raise(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    down = RecordingMailer(fail_with=MailFailure.TRANSIENT)
    sent = await run_once(
        clock=clock, sessionmaker=committed_sessionmaker, mailer=down, planners=[due_once(user)]
    )
    assert sent == 0
    up = RecordingMailer()
    clock.advance(timedelta(minutes=5))
    sent = await run_once(
        clock=clock, sessionmaker=committed_sessionmaker, mailer=up, planners=[due_once(user)]
    )
    assert sent == 1


async def test_failing_planner_does_not_block_others(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)

    async def broken(session: AsyncSession, now: datetime) -> list[PlannedMail]:
        raise RuntimeError("boom")

    mailer = RecordingMailer()
    await run_once(
        clock=clock,
        sessionmaker=committed_sessionmaker,
        mailer=mailer,
        planners=[broken, due_once(user)],
    )
    assert len(mailer.sent) == 1


async def test_failing_planner_is_logged_with_qualified_name(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def broken(session: AsyncSession, now: datetime) -> list[PlannedMail]:
        raise RuntimeError("boom")

    await run_once(
        clock=clock,
        sessionmaker=committed_sessionmaker,
        mailer=RecordingMailer(),
        planners=[broken],
    )
    messages = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
    assert any(broken.__qualname__ in m and __name__ in m for m in messages)


async def test_failing_planner_log_omits_exception_message(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = await make_committed_user(committed_sessionmaker)

    async def broken(session: AsyncSession, now: datetime) -> list[PlannedMail]:
        raise ValueError("Failing row contains (leak@example.test, secret body text)")

    mailer = RecordingMailer()
    await run_once(
        clock=clock,
        sessionmaker=committed_sessionmaker,
        mailer=mailer,
        planners=[broken, due_once(user)],
    )
    assert len(mailer.sent) == 1
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any(
        broken.__qualname__ in r.getMessage() and "ValueError" in r.getMessage() for r in errors
    )
    for r in errors:
        assert r.exc_info is None
        assert r.exc_text is None
    assert "leak@example.test" not in caplog.text
    assert "secret body text" not in caplog.text


async def test_planner_without_qualname_does_not_stop_the_run(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)

    async def broken(session: AsyncSession, now: datetime, *, flag: bool) -> list[PlannedMail]:
        raise RuntimeError("boom")

    mailer = RecordingMailer()
    await run_once(
        clock=clock,
        sessionmaker=committed_sessionmaker,
        mailer=mailer,
        planners=[functools.partial(broken, flag=True), due_once(user)],
    )
    assert len(mailer.sent) == 1


async def test_run_logs_sent_count_without_recipients(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    with caplog.at_level(logging.INFO):
        await run_once(
            clock=clock,
            sessionmaker=committed_sessionmaker,
            mailer=RecordingMailer(),
            planners=[due_once(user)],
        )
    messages = [r.getMessage() for r in caplog.records if r.name.startswith("giftmanager")]
    assert messages == ["Sent 1 mails"]


async def test_run_once_fails_expired_and_stuck_rows(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    now = clock.now()
    stuck = await add_committed_notification(
        committed_sessionmaker, status=NotificationStatus.SENDING
    )
    async with committed_sessionmaker() as s, s.begin():
        (await s.get_one(type(stuck), stuck.id)).claimed_at = now - timedelta(minutes=15)
    expired = await add_committed_notification(
        committed_sessionmaker, scheduled_for=now - timedelta(days=2), expires_at=now
    )
    await run_once(
        clock=clock, sessionmaker=committed_sessionmaker, mailer=RecordingMailer(), planners=[]
    )
    assert (await reload(committed_sessionmaker, stuck.id)).status is NotificationStatus.FAILED
    assert (await reload(committed_sessionmaker, expired.id)).status is NotificationStatus.FAILED


async def test_hung_run_times_out(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    monkeypatch.setattr(scheduler, "RUN_TIMEOUT", timedelta(seconds=0.2))
    with pytest.raises(TimeoutError):
        await run_once(
            clock=clock,
            sessionmaker=committed_sessionmaker,
            mailer=RecordingMailer(delay=30),
            planners=[due_once(user)],
        )


class ClockAdvancingMailer(RecordingMailer):
    def __init__(self, clock: FixedClock, step: timedelta) -> None:
        super().__init__()
        self.clock = clock
        self.step = step

    async def send(self, mail: Mail) -> None:
        await super().send(mail)
        self.clock.advance(self.step)


async def add_three_due(
    sessionmaker: async_sessionmaker[AsyncSession], now: datetime
) -> list[Notification]:
    return [
        await add_committed_notification(
            sessionmaker, scheduled_for=now - timedelta(hours=1), expires_at=now + timedelta(days=1)
        )
        for _ in range(3)
    ]


async def test_dispatch_stops_claiming_after_deadline(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    now = clock.now()
    rows = await add_three_due(committed_sessionmaker, now)
    mailer = ClockAdvancingMailer(clock, timedelta(minutes=2))
    sent = await dispatch_due(
        committed_sessionmaker, mailer, clock, until=now + timedelta(minutes=3)
    )
    assert sent == 2
    await assert_one_planned_two_sent(committed_sessionmaker, rows)


async def assert_one_planned_two_sent(
    sessionmaker: async_sessionmaker[AsyncSession], rows: list[Notification]
) -> None:
    statuses = [(await reload(sessionmaker, r.id)).status for r in rows]
    assert sorted(statuses) == [
        NotificationStatus.PLANNED,
        NotificationStatus.SENT,
        NotificationStatus.SENT,
    ]


async def test_run_once_stops_sending_after_send_budget(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    rows = await add_three_due(committed_sessionmaker, clock.now())
    mailer = ClockAdvancingMailer(clock, timedelta(minutes=2))
    sent = await run_once(
        clock=clock, sessionmaker=committed_sessionmaker, mailer=mailer, planners=[]
    )
    assert sent == 2
    await assert_one_planned_two_sent(committed_sessionmaker, rows)


async def test_hard_timeout_still_logs_sent_count(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
    clock: FixedClock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = clock.now()
    for _ in range(2):
        await add_committed_notification(
            committed_sessionmaker,
            scheduled_for=now - timedelta(hours=1),
            expires_at=now + timedelta(days=1),
        )

    class HangOnSecond(RecordingMailer):
        async def send(self, mail: Mail) -> None:
            if self.sent:
                await asyncio.sleep(30)
            await super().send(mail)

    monkeypatch.setattr(scheduler, "RUN_TIMEOUT", timedelta(seconds=2))
    with caplog.at_level(logging.INFO), pytest.raises(TimeoutError):
        await run_once(
            clock=clock, sessionmaker=committed_sessionmaker, mailer=HangOnSecond(), planners=[]
        )
    assert "Sent 1 mails" in [r.getMessage() for r in caplog.records]


async def test_serve_registers_the_interval_job(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[AsyncIOScheduler] = []
    ready = asyncio.Event()

    class RecordingScheduler(AsyncIOScheduler):
        def start(self, paused: bool = False) -> None:
            started.append(self)
            ready.set()

    monkeypatch.setattr(scheduler, "AsyncIOScheduler", RecordingScheduler)
    monkeypatch.setattr(scheduler, "get_clock", lambda: "clock")
    monkeypatch.setattr(scheduler, "get_sessionmaker", lambda: "sessionmaker")
    monkeypatch.setattr(scheduler, "get_mailer", lambda: "mailer")
    task = asyncio.create_task(scheduler._serve())  # pyright: ignore[reportPrivateUsage]
    await ready.wait()
    task.cancel()
    jobs: list[Any] = started[0].get_jobs()  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    (job,) = jobs
    assert job.func is run_once
    assert job.trigger.interval == scheduler.INTERVAL
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time is None
    assert job.kwargs == {"clock": "clock", "sessionmaker": "sessionmaker", "mailer": "mailer"}
    assert job.next_run_time <= datetime.now(UTC)


@pytest.mark.requirement("QZ-05")
async def test_engine_errors_do_not_contain_bound_parameters(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(db.get_settings(), "database_url", database_url)
    engine = db.get_engine.__wrapped__()
    try:
        async with engine.connect() as conn:
            with pytest.raises(DBAPIError) as raised:
                await conn.execute(text("SELECT :v FROM missing_table"), {"v": "secret-recipient"})
    finally:
        await engine.dispose()
    assert "secret-recipient" not in str(raised.value)


@pytest.mark.requirement("QZ-05")
def test_api_process_loads_no_scheduler_or_mail() -> None:
    code = (
        "import sys, giftmanager.main; "
        "print(sorted(m for m in ('apscheduler', 'aiosmtplib', 'giftmanager.scheduler') "
        "if m in sys.modules))"
    )
    out = subprocess.run(  # noqa: S603  # fixed argv, no untrusted input
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "APP_ENV": "test"},
    )
    assert out.stdout.strip() == "[]"
