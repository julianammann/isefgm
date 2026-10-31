"""Notification table (F-13)."""

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models.notification import Notification, NotificationType
from giftmanager.services.notification import dedup_key, format_day, local_at, local_date
from tests.notifications import make_notification, make_user, planned_mail


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
