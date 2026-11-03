"""Reminder two weeks before an own occasion (F-12)."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import partial
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gift import Gift
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
    ReferenceType,
)
from giftmanager.models.occasion import BIRTHDAY_TYPE_ID, Occasion, Recurrence, person_occasion
from giftmanager.models.person import Person
from giftmanager.models.user import User
from giftmanager.services.notification import (
    STATUS_LABELS,
    PlannedMail,
    active_recipients,
    dedup_key,
    format_day,
    local_at,
    local_date,
    local_midnight,
    skip_failed_account,
)
from giftmanager.services.occasion import next_occurrence
from giftmanager.services.ownership import owned

LEAD_DAYS = 14
OPEN_STATUSES = (GiftingStatus.IDEA, GiftingStatus.PLANNED)
NO_RECIPIENT = "ohne Empfänger"


def reminder_window(event: date) -> tuple[datetime, datetime]:
    """Opens at 08:00 local time 14 days before `event`, closes at local midnight on `event`."""
    return local_at(event - timedelta(days=LEAD_DAYS)), local_midnight(event)


class _Gifting(NamedTuple):
    occasion_id: UUID
    occasion_date: date | None
    created_at: datetime
    gift_id: UUID
    title: str
    status: GiftingStatus
    recipients: list[tuple[UUID, str]]


async def _giftings(
    session: AsyncSession, user_id: UUID, occasion_ids: list[UUID], events: set[date]
) -> list[_Gifting]:
    """Giftings of these occasions without a date or on one of `events`, ordered by gift title."""
    rows = await session.execute(
        select(
            Gifting.id,
            Gifting.occasion_id,
            Gifting.occasion_date,
            Gifting.created_at,
            Gift.id,
            Gift.title,
            Gifting.status,
            Person.id,
            Person.name,
        )
        .select_from(Gifting)
        .join(Gift, Gift.id == Gifting.gift_id)
        .outerjoin(gifting_person, gifting_person.c.gifting_id == Gifting.id)
        .outerjoin(Person, (Person.id == gifting_person.c.person_id) & (Person.owner_id == user_id))
        .where(
            Gift.owner_id == user_id,
            Gifting.occasion_id.in_(occasion_ids),
            or_(Gifting.occasion_date.is_(None), Gifting.occasion_date.in_(events)),
        )
        .order_by(func.lower(Gift.title), Gift.id, Gifting.id)
    )
    giftings: dict[UUID, _Gifting] = {}
    for gifting_id, occasion_id, day, created_at, gift_id, title, status, person_id, name in rows:
        gifting = giftings.setdefault(
            gifting_id, _Gifting(occasion_id, day, created_at, gift_id, title, status, [])
        )
        if person_id is not None:
            gifting.recipients.append((person_id, name))
    return list(giftings.values())


def _gaps(giftings: list[_Gifting], people: list[tuple[UUID, str]]) -> tuple[list[str], list[str]]:
    """(names of people without a gifting, "Title für Recipients|ohne Empfänger (Status): link" lines)."""
    covered = {person_id for g in giftings for person_id, _ in g.recipients}
    origin = get_settings().origin
    lines: list[str] = []
    for g in giftings:
        if g.status not in OPEN_STATUSES:
            continue
        names = sorted((name for _, name in g.recipients), key=str.lower)
        who = "für " + ", ".join(names) if names else NO_RECIPIENT
        lines.append(f"- {g.title} {who} ({STATUS_LABELS[g.status]}): {origin}/gifts/{g.gift_id}")
    missing = sorted((n for pid, n in people if pid not in covered), key=str.lower)
    return missing, lines


def _counting(
    giftings: list[_Gifting],
    occasion_id: UUID | None,
    event: date,
    next_from: Callable[[date], date | None],
) -> list[_Gifting]:
    """Giftings of the occasion that count for `event`.

    One without a date counts only for the first event from the day it was created on
    (`next_from`), so it does not cover the same occasion in later years.
    """
    return [
        g
        for g in giftings
        if g.occasion_id == occasion_id
        and (g.occasion_date or next_from(local_date(g.created_at))) == event
    ]


def _body(user: User, what: str, event: date, missing: list[str], lines: list[str]) -> str:
    parts = [f"Hallo {user.display_name},", f"am {format_day(event)} {what}."]
    if missing:
        parts.append("\n".join(["Noch ohne Beschenkung:", *(f"- {n}" for n in missing)]))
    if lines:
        parts.append("\n".join(["Noch nicht besorgt:", *lines]))
    parts.append(f"Alle Anlässe: {get_settings().origin}/occasions")
    return "\n\n".join(parts) + "\n"


def _mail(
    user: User,
    event: date,
    window: tuple[datetime, datetime],
    reference: tuple[ReferenceType, UUID],
    subject: str,
    what: str,
    gaps: tuple[list[str], list[str]],
) -> PlannedMail:
    opens, closes = window
    return PlannedMail(
        owner_id=user.id,
        recipient=user.email,
        type=NotificationType.OCCASION,
        reference_type=reference[0],
        reference_id=reference[1],
        event_date=event,
        interval=f"{LEAD_DAYS}d",
        scheduled_for=opens,
        expires_at=closes,
        subject=f"Erinnerung: {' '.join(subject.split())} am {format_day(event)}",
        body=_body(user, what, event, *gaps),
    )


# (occasion or person id, name, event, open window, next event from a day on)
type _Due = tuple[UUID, str, date, tuple[datetime, datetime], Callable[[date], date | None]]


def _open_window(event: date, now: datetime) -> tuple[datetime, datetime] | None:
    """The reminder window of `event` if it is open at `now`."""
    opens, closes = reminder_window(event)
    return (opens, closes) if opens <= now < closes else None


async def _account(session: AsyncSession, user: User, now: datetime) -> list[PlannedMail]:
    """Reminders of one account; at most five queries, however many are due."""
    today = local_date(now)
    occasions = await session.execute(
        owned(Occasion, user.id)
        .where(Occasion.date.is_not(None))
        .with_only_columns(Occasion.id, Occasion.name, Occasion.date, Occasion.recurrence)
    )
    due_occasions: list[_Due] = []
    for occasion_id, name, start, recurrence in occasions:
        next_from = partial(next_occurrence, start, recurrence)
        event = next_from(today)
        if event and (window := _open_window(event, now)):
            due_occasions.append((occasion_id, name, event, window, next_from))
    persons = await session.execute(
        owned(Person, user.id)
        .where(Person.birthday.is_not(None))
        .with_only_columns(Person.id, Person.name, Person.birthday)
    )
    due_birthdays: list[_Due] = []
    for person_id, name, birthday in persons:
        next_from = partial(next_occurrence, birthday, Recurrence.YEARLY)
        event = next_from(today)
        if event and (window := _open_window(event, now)):
            due_birthdays.append((person_id, name, event, window, next_from))
    if not (due_occasions or due_birthdays):
        return []

    due_ids = [occasion_id for occasion_id, *_ in due_occasions]
    people: dict[UUID, list[tuple[UUID, str]]] = {}
    if due_ids:
        rows = await session.execute(
            select(person_occasion.c.occasion_id, Person.id, Person.name)
            .join(person_occasion, person_occasion.c.person_id == Person.id)
            .where(person_occasion.c.occasion_id.in_(due_ids), Person.owner_id == user.id)
        )
        for occasion_id, person_id, name in rows:
            people.setdefault(occasion_id, []).append((person_id, name))
    birthday_occasion: UUID | None = None
    if due_birthdays:
        birthday_occasion = await session.scalar(
            owned(Occasion, user.id)
            .where(Occasion.occasion_type_id == BIRTHDAY_TYPE_ID, Occasion.date.is_(None))
            .with_only_columns(Occasion.id)
            .order_by(Occasion.id)
            .limit(1)
        )
    occasion_ids = due_ids + ([birthday_occasion] if birthday_occasion else [])
    events = {event for _, _, event, _, _ in due_occasions + due_birthdays}
    giftings = await _giftings(session, user.id, occasion_ids, events) if occasion_ids else []

    mails: list[PlannedMail] = []
    for occasion_id, name, event, window, next_from in due_occasions:
        counting = _counting(giftings, occasion_id, event, next_from)
        gaps = _gaps(counting, people.get(occasion_id, []))
        if gaps[0] or gaps[1]:
            reference = (ReferenceType.OCCASION, occasion_id)
            mails.append(_mail(user, event, window, reference, name, f"ist {name}", gaps))
    for person_id, name, event, window, next_from in due_birthdays:
        theirs = [
            g
            for g in _counting(giftings, birthday_occasion, event, next_from)
            if any(pid == person_id for pid, _ in g.recipients)
        ]
        gaps = _gaps(theirs, [(person_id, name)])
        if gaps[0] or gaps[1]:
            reference = (ReferenceType.PERSON, person_id)
            what = f"hat {name} Geburtstag"
            mails.append(
                _mail(user, event, window, reference, f"Geburtstag von {name}", what, gaps)
            )
    return mails


async def due(session: AsyncSession, now: datetime) -> list[PlannedMail]:
    """Reminders of own occasions and birthdays whose window is open and that still have gaps.

    A reminder not sent yet that is no longer due (gaps closed, date moved) is deleted, so a
    retry after a transient failure does not send it; if the gap opens again it is planned anew.
    """
    mails: list[PlannedMail] = []
    # shortcut: up to six queries per account, fine for the test accounts; batch across accounts if there are many.
    for user in await active_recipients(session):
        # Mails are kept only when the whole account succeeded.
        async with skip_failed_account(session, user):
            account = await _account(session, user, now)
            await session.execute(
                delete(Notification).where(
                    Notification.owner_id == user.id,
                    Notification.type == NotificationType.OCCASION,
                    Notification.status == NotificationStatus.PLANNED,
                    Notification.dedup_key.not_in([dedup_key(m) for m in account]),
                )
            )
            mails += account
    return mails
