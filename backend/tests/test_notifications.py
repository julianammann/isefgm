"""Notification table (F-13)."""

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.clock import Clock
from giftmanager.core.mail import Mail, MailFailure
from giftmanager.models.notification import Notification, NotificationStatus, NotificationType
from giftmanager.models.user import UserStatus
from giftmanager.services.notification import (
    active_recipients,
    dedup_key,
    dispatch_due,
    expire,
    fail_stuck,
    format_day,
    local_at,
    local_date,
    plan,
)
from tests.conftest import FixedClock
from tests.mail import RecordingMailer
from tests.notifications import (
    add_committed_notification,
    make_committed_user,
    make_notification,
    make_user,
    planned_mail,
    reload,
    statuses_of,
)


@pytest.mark.requirement("F-13")
async def test_notification_rows_go_with_the_account(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    session.add(make_notification(user, dedup_key="k1"))
    await session.flush()
    await session.delete(user)
    await session.flush()
    assert await session.scalar(select(func.count()).select_from(Notification)) == 0


@pytest.mark.requirement("F-13", "Q-02")
async def test_dedup_key_is_unique(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    session.add_all(
        [make_notification(user, dedup_key="k1"), make_notification(user, dedup_key="k1")]
    )
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.requirement("QZ-09")
@pytest.mark.parametrize(
    ("day", "utc"),
    [
        (date(2026, 11, 12), datetime(2026, 11, 12, 7, 0, tzinfo=UTC)),  # CET
        (date(2026, 7, 1), datetime(2026, 7, 1, 6, 0, tzinfo=UTC)),  # CEST
        (date(2026, 3, 29), datetime(2026, 3, 29, 6, 0, tzinfo=UTC)),  # DST starts that night
        (date(2026, 10, 25), datetime(2026, 10, 25, 7, 0, tzinfo=UTC)),  # DST ends that night
    ],
)
def test_local_at_is_eight_in_berlin(day: date, utc: datetime) -> None:
    assert local_at(day) == utc


@pytest.mark.requirement("QZ-09")
def test_local_date_switches_at_berlin_midnight() -> None:
    assert local_date(datetime(2026, 11, 30, 22, 59, tzinfo=UTC)) == date(2026, 11, 30)
    assert local_date(datetime(2026, 11, 30, 23, 0, tzinfo=UTC)) == date(2026, 12, 1)


@pytest.mark.requirement("F-13", "Q-02")
def test_dedup_key_covers_account_reference_date_type_and_interval() -> None:
    owner, ref = UUID(int=1), UUID(int=2)
    mail = planned_mail(
        owner_id=owner,
        type=NotificationType.CHRISTMAS,
        reference_id=ref,
        event_date=date(2026, 12, 24),
        interval="2026-11-16",
    )
    assert dedup_key(mail) == f"christmas:{owner}:{ref}:2026-12-24:2026-11-16"
    assert (
        dedup_key(replace(mail, reference_id=None)) == f"christmas:{owner}:-:2026-12-24:2026-11-16"
    )


@pytest.mark.requirement("F-10")
def test_format_day_is_day_and_month_with_dot() -> None:
    assert format_day(date(2026, 12, 3)) == "03.12."


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_plan_twice_creates_one_row(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    mail = planned_mail(owner_id=user.id)
    assert await plan(session, [mail]) == 1
    assert await plan(session, [mail]) == 0
    assert await session.scalar(select(func.count()).select_from(Notification)) == 1


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_parallel_planning_creates_one_row(
    committed_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    mail = planned_mail(owner_id=user.id, recipient=user.email)

    async def run() -> int:
        async with committed_sessionmaker() as s, s.begin():
            return await plan(s, [mail])

    assert sorted(await asyncio.gather(run(), run())) == [0, 1]


@pytest.mark.requirement("Q-04")
async def test_active_recipients_skip_reserved_and_deleted(
    session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    keep = await make_user(session, "konto@isefgm.localhost")
    reserved = await make_user(session, "test1@example.org")
    gone = await make_user(session, "weg@isefgm.localhost")
    gone.status = UserStatus.DELETED
    await session.flush()
    with caplog.at_level(logging.INFO):
        assert [u.id for u in await active_recipients(session)] == [keep.id]
    messages = [r.getMessage() for r in caplog.records]
    assert any(str(reserved.id) in m for m in messages)
    assert not any("example.org" in m for m in messages)


Maker = async_sessionmaker[AsyncSession]
SEND_TIME = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_dispatch_sends_and_records(committed_sessionmaker: Maker, clock: Clock) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    row = await add_committed_notification(committed_sessionmaker)
    mailer = RecordingMailer()
    assert await dispatch_due(committed_sessionmaker, mailer, clock) == 1
    assert mailer.sent == [Mail(to=row.recipient, subject="Betreff", body="Text")]
    stored = await reload(committed_sessionmaker, row.id)
    assert (stored.status, stored.sent_at, stored.error) == (
        NotificationStatus.SENT,
        clock.now(),
        None,
    )


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_not_sent_before_scheduled_for(committed_sessionmaker: Maker, clock: Clock) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    await add_committed_notification(
        committed_sessionmaker, scheduled_for=clock.now() + timedelta(minutes=1)
    )
    assert await dispatch_due(committed_sessionmaker, RecordingMailer(), clock) == 0


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_parallel_dispatch_sends_each_once(
    committed_sessionmaker: Maker, clock: Clock
) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    for i in range(10):
        await add_committed_notification(committed_sessionmaker, dedup_key=f"k{i}")
    mailer = RecordingMailer(delay=0.01)
    sent = await asyncio.gather(
        *(dispatch_due(committed_sessionmaker, mailer, clock) for _ in range(2))
    )
    assert sum(sent) == 10
    assert len(mailer.sent) == 10


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_transient_failure_keeps_rows_planned_and_stops(
    committed_sessionmaker: Maker, clock: Clock
) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    for i in range(2):
        await add_committed_notification(committed_sessionmaker, dedup_key=f"k{i}")
    mailer = RecordingMailer(fail_with=MailFailure.TRANSIENT)
    assert await dispatch_due(committed_sessionmaker, mailer, clock) == 0
    assert await statuses_of(committed_sessionmaker) == [NotificationStatus.PLANNED] * 2
    mailer.fail_with = None
    assert await dispatch_due(committed_sessionmaker, mailer, clock) == 2


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_permanent_failure_is_final(committed_sessionmaker: Maker, clock: Clock) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    row = await add_committed_notification(committed_sessionmaker)
    await dispatch_due(
        committed_sessionmaker, RecordingMailer(fail_with=MailFailure.PERMANENT), clock
    )
    mailer = RecordingMailer()
    await dispatch_due(committed_sessionmaker, mailer, clock)
    assert mailer.sent == []
    assert (await reload(committed_sessionmaker, row.id)).status is NotificationStatus.FAILED


@pytest.mark.requirement("F-13", "Q-02", "QZ-05")
async def test_unclear_result_is_logged_and_not_resent(
    committed_sessionmaker: Maker, clock: Clock, caplog: pytest.LogCaptureFixture
) -> None:
    clock.current = SEND_TIME  # pyright: ignore[reportAttributeAccessIssue]
    row = await add_committed_notification(committed_sessionmaker)
    await dispatch_due(
        committed_sessionmaker, RecordingMailer(fail_with=MailFailure.UNCLEAR), clock
    )
    stored = await reload(committed_sessionmaker, row.id)
    assert stored.status is NotificationStatus.FAILED
    assert stored.error is not None
    assert stored.error.startswith("Versandergebnis unklar")
    assert any(r.levelname == "WARNING" and str(row.id) in r.getMessage() for r in caplog.records)
    mailer = RecordingMailer()
    await dispatch_due(committed_sessionmaker, mailer, clock)
    assert mailer.sent == []


@pytest.mark.requirement("Q-02", "QZ-05")
async def test_stuck_sending_fails_after_15_minutes(
    session: AsyncSession, clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    stuck = make_notification(user, dedup_key="a", status=NotificationStatus.SENDING)
    stuck.claimed_at = clock.now() - timedelta(minutes=15)
    fresh = make_notification(user, dedup_key="b", status=NotificationStatus.SENDING)
    fresh.claimed_at = clock.now() - timedelta(minutes=14, seconds=59)
    session.add_all([stuck, fresh])
    await session.flush()
    assert await fail_stuck(session, clock.now()) == 1
    await session.refresh(stuck)
    await session.refresh(fresh)
    assert (stuck.status, fresh.status) == (NotificationStatus.FAILED, NotificationStatus.SENDING)
    claimed_at = clock.now() - timedelta(minutes=15)
    assert stuck.error == "Versandergebnis unklar: hängt seit " + claimed_at.isoformat()
    assert any(r.levelname == "WARNING" and str(stuck.id) in r.getMessage() for r in caplog.records)


@pytest.mark.requirement("F-13")
async def test_expired_planned_row_fails(session: AsyncSession, clock: FixedClock) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    row = make_notification(user, dedup_key="a", expires_at=clock.now())
    session.add(row)
    await session.flush()
    assert await expire(session, clock.now()) == 1
    await session.refresh(row)
    assert (row.status, row.error) == (NotificationStatus.FAILED, "Zeitfenster abgelaufen")
