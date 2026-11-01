"""Christmas and Easter status overview (F-11)."""

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gift import Gift, gift_occasion, gift_person
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.notification import NotificationType, ReferenceType
from giftmanager.models.occasion import CHRISTMAS_TYPE_ID, EASTER_TYPE_ID, Occasion, OccasionRule
from giftmanager.models.person import Person
from giftmanager.models.user import User
from giftmanager.services.notification import (
    STATUS_LABELS,
    PlannedMail,
    active_recipients,
    local_at,
    local_date,
    local_midnight,
)
from giftmanager.services.occasion import rule_date
from giftmanager.services.ownership import owned

START_DAYS = 42
Line = tuple[UUID, str, GiftingStatus]  # gift id, title, status of one gifting
SEASONS = (
    (OccasionRule.CHRISTMAS, CHRISTMAS_TYPE_ID, NotificationType.CHRISTMAS, "Weihnachten"),
    (OccasionRule.EASTER, EASTER_TYPE_ID, NotificationType.EASTER, "Ostern"),
)


def send_dates(event: date) -> list[date]:
    """Send days: the start 42 days before `event`, then every Monday before `event`."""
    start = event - timedelta(days=START_DAYS)
    days = [start]
    monday = start + timedelta(days=7 - start.weekday())
    while monday < event:
        days.append(monday)
        monday += timedelta(days=7)
    return days


def open_send(event: date, now: datetime) -> tuple[date, datetime, datetime] | None:
    """(send day, window start, window end) of the open window, or None if none is open.

    A window opens at 08:00 local time on its send day and closes at 08:00 on the next send day;
    the last one closes at local midnight on `event`.
    """
    days = send_dates(event)
    for index, send in enumerate(days):
        start = local_at(send)
        end = local_at(days[index + 1]) if index + 1 < len(days) else local_midnight(event)
        if start <= now < end:
            return send, start, end
    return None


async def _entries(
    session: AsyncSession, user_id: UUID, occasion_id: UUID, event: date
) -> tuple[
    dict[UUID, tuple[str, list[Line]]],
    list[Line],
]:
    """(per person: name and giftings, giftings without recipient) of the occasion on `event`."""
    rows = await session.execute(
        select(Person.id, Person.name, Gift.id, Gift.title, Gifting.status)
        .select_from(Gifting)
        .join(Gift, Gift.id == Gifting.gift_id)
        .outerjoin(gifting_person, gifting_person.c.gifting_id == Gifting.id)
        .outerjoin(Person, (Person.id == gifting_person.c.person_id) & (Person.owner_id == user_id))
        .where(
            Gift.owner_id == user_id,
            Gifting.occasion_id == occasion_id,
            or_(Gifting.occasion_date.is_(None), Gifting.occasion_date == event),
        )
        .order_by(func.lower(Gift.title), Gift.id)
    )
    people: dict[UUID, tuple[str, list[Line]]] = {}
    nobody: list[Line] = []
    for person_id, name, gift_id, title, status in rows:
        if person_id is None:
            nobody.append((gift_id, title, status))
        else:
            people.setdefault(person_id, (name, []))[1].append((gift_id, title, status))
    return people, nobody


async def _idea_people(
    session: AsyncSession, user_id: UUID, occasion_id: UUID
) -> dict[UUID, tuple[str, list[str]]]:
    """Per person: name and titles of ideas of the occasion not yet given to them."""
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
    rows = await session.execute(
        select(Person.id, Person.name, Gift.title)
        .select_from(gift_occasion)
        .join(Gift, Gift.id == gift_occasion.c.gift_id)
        .join(gift_person, gift_person.c.gift_id == Gift.id)
        .join(Person, Person.id == gift_person.c.person_id)
        .where(
            gift_occasion.c.occasion_id == occasion_id,
            Gift.owner_id == user_id,
            Person.owner_id == user_id,
            ~given_to_person,
        )
        .order_by(func.lower(Gift.title), Gift.id)
    )
    ideas: dict[UUID, tuple[str, list[str]]] = {}
    for person_id, name, title in rows:
        ideas.setdefault(person_id, (name, []))[1].append(title)
    return ideas


def _body(
    user: User,
    label: str,
    event: date,
    people: dict[UUID, tuple[str, list[Line]]],
    ideas: dict[UUID, tuple[str, list[str]]],
    nobody: list[Line],
) -> str:
    origin = get_settings().origin

    def lines(giftings: list[Line]) -> list[str]:
        return [
            f"- {title} ({STATUS_LABELS[status]}): {origin}/gifts/{gift_id}"
            for gift_id, title, status in giftings
        ]

    entries = {pid: (name, lines(g)) for pid, (name, g) in people.items()}
    for pid, (name, titles) in ideas.items():
        entries.setdefault(pid, (name, [f"- noch keine Beschenkung, Ideen: {', '.join(titles)}"]))
    blocks = [
        "\n".join([name, *body])
        for name, body in sorted(entries.values(), key=lambda e: e[0].lower())
    ]
    if nobody:
        blocks.append("\n".join(["Ohne Empfänger", *lines(nobody)]))
    return (
        f"Hallo {user.display_name},\n\n"
        f"Stand für {label} am {event.day:02d}.{event.month:02d}.{event.year}:\n\n"
        + "\n\n".join(blocks)
        + f"\n\nAlle Geschenkideen: {origin}/gifts\n"
    )


async def due(session: AsyncSession, now: datetime) -> list[PlannedMail]:
    """Overview mails of the open send windows, one per account and season with recipients."""
    mails: list[PlannedMail] = []
    for rule, type_id, mail_type, label in SEASONS:
        event = rule_date(rule, local_date(now))
        window = open_send(event, now) if event else None
        if event is None or window is None:
            continue
        send_day, scheduled_for, expires_at = window
        # shortcut: three queries per account and open season, fine for the test accounts, revisit with many accounts.
        for user in await active_recipients(session):
            occasion_id = await session.scalar(
                owned(Occasion, user.id)
                .where(Occasion.occasion_type_id == type_id, Occasion.date.is_(None))
                .with_only_columns(Occasion.id)
            )
            if occasion_id is None:
                continue
            people, nobody = await _entries(session, user.id, occasion_id, event)
            ideas = await _idea_people(session, user.id, occasion_id)
            if not (people or ideas or nobody):
                continue
            mails.append(
                PlannedMail(
                    owner_id=user.id,
                    recipient=user.email,
                    type=mail_type,
                    reference_type=ReferenceType.OCCASION,
                    reference_id=occasion_id,
                    event_date=event,
                    interval=send_day.isoformat(),
                    scheduled_for=scheduled_for,
                    expires_at=expires_at,
                    subject=f"{label} {event.year}: Stand der Geschenke",
                    body=_body(user, label, event, people, ideas, nobody),
                )
            )
    return mails
