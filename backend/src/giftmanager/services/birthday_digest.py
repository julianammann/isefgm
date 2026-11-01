"""Monthly digest of next month's birthdays (F-10)."""

from datetime import date, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import exists, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gift import Gift, gift_person
from giftmanager.models.gifting import Gifting, GiftingStatus
from giftmanager.models.notification import NotificationType
from giftmanager.models.person import Person
from giftmanager.models.user import User
from giftmanager.services.notification import (
    PlannedMail,
    active_recipients,
    format_day,
    local_at,
    local_date,
)

MONTH_NAMES = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def _next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def digest_window(now: datetime) -> tuple[date, datetime, datetime]:
    """(first day of the birthday month, send time, end of the send window).

    Mails go out on the 1st at 08:00 local time; before that moment on the 1st the previous
    month's window still applies.
    """
    send_day = local_date(now).replace(day=1)
    if now < local_at(send_day):
        send_day = (send_day - timedelta(days=1)).replace(day=1)
    birthday_month = _next_month(send_day)
    return birthday_month, local_at(send_day), local_at(birthday_month)


async def _ideas_by_person(session: AsyncSession, person_ids: list[UUID]) -> dict[UUID, list[Gift]]:
    given = exists().where(Gifting.gift_id == Gift.id, Gifting.status == GiftingStatus.GIVEN)
    rows = await session.execute(
        select(gift_person.c.person_id, Gift)
        .join(Gift, Gift.id == gift_person.c.gift_id)
        .where(gift_person.c.person_id.in_(person_ids), ~given)
        .order_by(func.lower(Gift.title), Gift.id)
    )
    ideas: dict[UUID, list[Gift]] = {}
    for person_id, gift in rows:
        ideas.setdefault(person_id, []).append(gift)
    return ideas


def _body(user: User, month: date, people: list[Person], ideas: dict[UUID, list[Gift]]) -> str:
    origin = get_settings().origin
    month_name = MONTH_NAMES[month.month - 1]
    blocks: list[str] = []
    for person in people:
        birthday = cast(date, person.birthday)  # the month filter excludes NULL
        lines = [f"{format_day(birthday)} {person.name}"]
        gifts = ideas.get(person.id, [])
        lines += [f"- {g.title}: {origin}/gifts/{g.id}" for g in gifts] or ["- noch keine Ideen"]
        blocks.append("\n".join(lines))
    return (
        f"Hallo {user.display_name},\n\n"
        f"im {month_name} haben Geburtstag:\n\n"
        + "\n\n".join(blocks)
        + f"\n\nAlle Personen: {origin}/persons\n"
    )


async def due(session: AsyncSession, now: datetime) -> list[PlannedMail]:
    """Digest mails of the current window, one per account with a birthday in the month."""
    month, scheduled_for, expires_at = digest_window(now)
    mails: list[PlannedMail] = []
    # shortcut: one query per account, fine for the test accounts, revisit with many accounts.
    for user in await active_recipients(session):
        people = list(
            await session.scalars(
                select(Person)
                .where(Person.owner_id == user.id, extract("month", Person.birthday) == month.month)
                .order_by(extract("day", Person.birthday), func.lower(Person.name), Person.id)
            )
        )
        if not people:
            continue
        ideas = await _ideas_by_person(session, [p.id for p in people])
        mails.append(
            PlannedMail(
                owner_id=user.id,
                recipient=user.email,
                type=NotificationType.BIRTHDAY,
                reference_type=None,
                reference_id=None,
                event_date=month,
                interval="monthly",
                scheduled_for=scheduled_for,
                expires_at=expires_at,
                subject=f"Geburtstage im {MONTH_NAMES[month.month - 1]}",
                body=_body(user, month, people, ideas),
            )
        )
    return mails
