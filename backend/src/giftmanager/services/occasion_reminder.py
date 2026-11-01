"""Reminder two weeks before an own occasion (F-12)."""

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gift import Gift
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.notification import NotificationType, ReferenceType
from giftmanager.models.occasion import BIRTHDAY_TYPE_ID, Occasion, Recurrence, person_occasion
from giftmanager.models.person import Person
from giftmanager.models.user import User
from giftmanager.services.notification import (
    STATUS_LABELS,
    PlannedMail,
    active_recipients,
    format_day,
    local_at,
    local_date,
    local_midnight,
)
from giftmanager.services.occasion import next_occurrence
from giftmanager.services.ownership import owned

LEAD_DAYS = 14
OPEN_STATUSES = (GiftingStatus.IDEA, GiftingStatus.PLANNED)
NO_RECIPIENT = "ohne Empfänger"


def reminder_window(event: date) -> tuple[datetime, datetime]:
    """Opens at 08:00 local time 14 days before `event`, closes at local midnight on `event`."""
    return local_at(event - timedelta(days=LEAD_DAYS)), local_midnight(event)


async def _gaps(
    session: AsyncSession,
    user_id: UUID,
    occasion_id: UUID | None,
    event: date,
    people: list[tuple[UUID, str]],
    only_person: UUID | None = None,
) -> tuple[list[str], list[str]]:
    """(names of people without a gifting, "Title für Recipients|ohne Empfänger (Status): link" lines).

    `only_person` restricts the counting giftings to those with this recipient; without an
    `occasion_id` nothing counts.
    """
    if occasion_id is None:
        return sorted((n for _, n in people), key=str.lower), []
    rows = await session.execute(
        select(Gifting.id, Gift.id, Gift.title, Gifting.status, Person.id, Person.name)
        .select_from(Gifting)
        .join(Gift, Gift.id == Gifting.gift_id)
        .outerjoin(gifting_person, gifting_person.c.gifting_id == Gifting.id)
        .outerjoin(Person, (Person.id == gifting_person.c.person_id) & (Person.owner_id == user_id))
        .where(
            Gift.owner_id == user_id,
            Gifting.occasion_id == occasion_id,
            or_(Gifting.occasion_date.is_(None), Gifting.occasion_date == event),
            true()
            if only_person is None
            else Gifting.id.in_(
                select(gifting_person.c.gifting_id).where(gifting_person.c.person_id == only_person)
            ),
        )
        .order_by(func.lower(Gift.title), Gift.id, Gifting.id)
    )
    covered: set[UUID] = set()
    open_giftings: dict[UUID, tuple[UUID, str, GiftingStatus, list[str]]] = {}
    for gifting_id, gift_id, title, status, person_id, name in rows:
        if person_id is not None:
            covered.add(person_id)
        if status in OPEN_STATUSES:
            recipients = open_giftings.setdefault(gifting_id, (gift_id, title, status, []))[3]
            if name is not None:
                recipients.append(name)
    origin = get_settings().origin
    lines = [
        f"- {title} {'für ' + ', '.join(sorted(names, key=str.lower)) if names else NO_RECIPIENT} "
        f"({STATUS_LABELS[status]}): {origin}/gifts/{gift_id}"
        for gift_id, title, status, names in open_giftings.values()
    ]
    missing = sorted((n for pid, n in people if pid not in covered), key=str.lower)
    return missing, lines


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
    reference: tuple[ReferenceType, UUID],
    subject: str,
    what: str,
    gaps: tuple[list[str], list[str]],
) -> PlannedMail:
    opens, closes = reminder_window(event)
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


def _open(event: date, now: datetime) -> bool:
    opens, closes = reminder_window(event)
    return opens <= now < closes


async def due(session: AsyncSession, now: datetime) -> list[PlannedMail]:
    """Reminders of own occasions and birthdays whose window is open and that still have gaps."""
    mails: list[PlannedMail] = []
    today = local_date(now)
    # shortcut: two queries per account (occasions, persons) plus up to two per due occasion (people, giftings),
    # and one for the birthday occasion plus up to one per due birthday; fine for the test accounts, revisit with many accounts.
    for user in await active_recipients(session):
        occasions = await session.execute(
            owned(Occasion, user.id)
            .where(Occasion.date.is_not(None))
            .with_only_columns(Occasion.id, Occasion.name, Occasion.date, Occasion.recurrence)
        )
        for occasion_id, name, start, recurrence in occasions:
            event = next_occurrence(start, recurrence, today)
            if event is None or not _open(event, now):
                continue
            people = await session.execute(
                select(Person.id, Person.name)
                .join(person_occasion, person_occasion.c.person_id == Person.id)
                .where(person_occasion.c.occasion_id == occasion_id, Person.owner_id == user.id)
            )
            gaps = await _gaps(session, user.id, occasion_id, event, [(i, n) for i, n in people])
            if gaps[0] or gaps[1]:
                reference = (ReferenceType.OCCASION, occasion_id)
                mails.append(_mail(user, event, reference, name, f"ist {name}", gaps))
        birthday_occasion: UUID | None = None
        birthday_occasion_loaded = False
        persons = await session.execute(
            owned(Person, user.id)
            .where(Person.birthday.is_not(None))
            .with_only_columns(Person.id, Person.name, Person.birthday)
        )
        for person_id, name, birthday in persons:
            event = next_occurrence(birthday, Recurrence.YEARLY, today)
            if event is None or not _open(event, now):
                continue
            if not birthday_occasion_loaded:
                birthday_occasion = await session.scalar(
                    owned(Occasion, user.id)
                    .where(Occasion.occasion_type_id == BIRTHDAY_TYPE_ID, Occasion.date.is_(None))
                    .with_only_columns(Occasion.id)
                    .order_by(Occasion.id)
                    .limit(1)
                )
                birthday_occasion_loaded = True
            gaps = await _gaps(
                session, user.id, birthday_occasion, event, [(person_id, name)], person_id
            )
            if gaps[0] or gaps[1]:
                reference = (ReferenceType.PERSON, person_id)
                mails.append(
                    _mail(
                        user,
                        event,
                        reference,
                        f"Geburtstag von {name}",
                        f"hat {name} Geburtstag",
                        gaps,
                    )
                )
    return mails
