"""Scheduler run: plan, clean up and send (F-13, QZ-05)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.mail import MailFailure
from giftmanager.models.user import User
from giftmanager.scheduler import Planner, run_once
from giftmanager.services.notification import PlannedMail
from tests.conftest import FixedClock
from tests.mail import RecordingMailer
from tests.notifications import make_committed_user, planned_mail

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
