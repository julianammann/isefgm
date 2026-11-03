"""Monthly digest of next month's birthdays (F-10)."""

from datetime import date, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import exists, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gift import Gift, gift_person
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.notification import NotificationType
from giftmanager.models.occasion import Recurrence
from giftmanager.models.person import Person
from giftmanager.models.user import User
from giftmanager.services.notification import (
    PlannedMail,
    active_recipients,
    format_day,
    local_at,
    local_date,
)
from giftmanager.services.occasion import next_occurrence
from giftmanager.services.ownership import owned

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


async def _ideas_by_person(
    session: AsyncSession, user_id: UUID, person_ids: list[UUID]
) -> dict[UUID, list[tuple[UUID, str]]]:
    """Per person: linked gifts not yet given to them, plus gifts of their open giftings."""
    given_to_person = (
        exists()
        .where(
            Gifting.gift_id == Gift.id,
            Gifting.status == GiftingStatus.GIVEN,
            gifting_person.c.gifting_id == Gifting.id,
            gifting_person.c.person_id == gift_person.c.person_id,
        )
        .correlate(Gift, gift_person)
    )
    linked = (
        select(
            gift_person.c.person_id.label("person_id"),
            Gift.id.label("gift_id"),
            Gift.title.label("title"),
        )
        .join(Gift, Gift.id == gift_person.c.gift_id)
        .where(gift_person.c.person_id.in_(person_ids), Gift.owner_id == user_id, ~given_to_person)
    )
    planned = (
        select(
            gifting_person.c.person_id.label("person_id"),
            Gift.id.label("gift_id"),
            Gift.title.label("title"),
        )
        .join(Gifting, Gifting.id == gifting_person.c.gifting_id)
        .join(Gift, Gift.id == Gifting.gift_id)
        .where(
            gifting_person.c.person_id.in_(person_ids),
            Gift.owner_id == user_id,
            Gifting.status.in_((GiftingStatus.IDEA, GiftingStatus.PLANNED, GiftingStatus.ACQUIRED)),
        )
    )
    both = linked.union(planned).subquery()  # UNION drops a gift listed by both parts
    rows = await session.execute(
        select(both.c.person_id, both.c.gift_id, both.c.title).order_by(
            func.lower(both.c.title), both.c.gift_id
        )
    )
    ideas: dict[UUID, list[tuple[UUID, str]]] = {}
    for person_id, gift_id, title in rows:
        ideas.setdefault(person_id, []).append((gift_id, title))
    return ideas


def _body(
    user: User, month: date, people: list[Person], ideas: dict[UUID, list[tuple[UUID, str]]]
) -> str:
    origin = get_settings().origin
    month_name = MONTH_NAMES[month.month - 1]
    blocks: list[str] = []
    for person in people:
        birthday = cast(date, person.birthday)  # the month filter excludes NULL
        # same day as the backend shows it: 29.02. becomes 28.02. outside leap years
        day = cast(date, next_occurrence(birthday, Recurrence.YEARLY, month))
        lines = [f"{format_day(day)} {person.name}"]
        gifts = ideas.get(person.id, [])
        lines += [f"- {title}: {origin}/gifts/{gift_id}" for gift_id, title in gifts] or [
            "- noch keine Ideen"
        ]
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
    # shortcut: two queries per account (people, ideas), fine for the test accounts, revisit with many accounts.
    for user in await active_recipients(session):
        people = list(
            await session.scalars(
                owned(Person, user.id)
                .where(extract("month", Person.birthday) == month.month)
                .order_by(extract("day", Person.birthday), func.lower(Person.name), Person.id)
            )
        )
        if not people:
            continue
        ideas = await _ideas_by_person(session, user.id, [p.id for p in people])
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
