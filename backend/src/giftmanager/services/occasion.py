"""Occasion types and occasions of an account (F-03), the rule occasions Geburtstag,
Weihnachten and Ostern included. No HTTP in here."""

import calendar
import datetime as dt
import uuid

from sqlalchemy import ColumnElement, case, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import ConflictError, NotFoundError
from giftmanager.models import (
    RULE_NAMES,
    RULE_TYPES,
    Occasion,
    OccasionRule,
    OccasionType,
    Person,
    Recurrence,
)
from giftmanager.services import gifting as gifting_service
from giftmanager.services.ownership import get_all_owned, get_owned, owned, paginate


def _visible_types(owner_id: uuid.UUID) -> ColumnElement[bool]:
    """System-wide types plus the account's own types."""
    return or_(OccasionType.owner_id.is_(None), OccasionType.owner_id == owner_id)


async def list_occasion_types(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[OccasionType], int]:
    """Return one page of the types the owner can use, system-wide ones first."""
    return await paginate(
        session,
        select(OccasionType)
        .where(_visible_types(owner_id))
        .order_by(OccasionType.owner_id.is_not(None), func.lower(OccasionType.name)),
        limit=limit,
        offset=offset,
    )


async def get_occasion_type(
    session: AsyncSession, owner_id: uuid.UUID, occasion_type_id: uuid.UUID
) -> OccasionType:
    """Return a system-wide type or one of the owner's types."""
    occasion_type = await session.scalar(
        select(OccasionType).where(OccasionType.id == occasion_type_id, _visible_types(owner_id))
    )
    if occasion_type is None:
        raise NotFoundError("Occasion type not found")
    return occasion_type


async def list_occasions(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Occasion], int]:
    """Return one page of the owner's occasions and the total count: the rule occasions first
    (Geburtstag, Weihnachten, Ostern), then the others by month and day (year ignored)."""
    rule_rank = case(
        {type_id: rank for rank, type_id in enumerate(RULE_TYPES)},
        value=Occasion.occasion_type_id,
        else_=len(RULE_TYPES),
    )
    return await paginate(
        session,
        owned(Occasion, owner_id).order_by(
            rule_rank,
            extract("month", Occasion.date),
            extract("day", Occasion.date),
            func.lower(Occasion.name),
            Occasion.id,
        ),
        limit=limit,
        offset=offset,
    )


async def get_occasion(
    session: AsyncSession, owner_id: uuid.UUID, occasion_id: uuid.UUID
) -> Occasion:
    """Return the owner's occasion."""
    return await get_owned(session, Occasion, owner_id, occasion_id)


async def create_occasion(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    name: str,
    date: dt.date,
    recurrence: Recurrence,
    occasion_type_id: uuid.UUID | None,
    person_ids: list[uuid.UUID],
) -> Occasion:
    """Create an occasion for the owner, linked to some of the owner's people."""
    if occasion_type_id is not None:
        await get_occasion_type(session, owner_id, occasion_type_id)
    occasion = Occasion(
        owner_id=owner_id,
        name=name,
        date=date,
        recurrence=recurrence,
        occasion_type_id=occasion_type_id,
        people=await get_all_owned(session, Person, owner_id, person_ids),
    )
    session.add(occasion)
    await session.flush()
    await _reload_people(session, occasion)
    return occasion


async def update_occasion(
    session: AsyncSession,
    owner_id: uuid.UUID,
    occasion_id: uuid.UUID,
    *,
    name: str,
    date: dt.date,
    recurrence: Recurrence,
    occasion_type_id: uuid.UUID | None,
    person_ids: list[uuid.UUID],
) -> Occasion:
    """Replace all editable fields and links of the owner's occasion."""
    occasion = await _get_editable_occasion(session, owner_id, occasion_id)
    if occasion_type_id is not None:
        await get_occasion_type(session, owner_id, occasion_type_id)
    # Resolve the links first, so a foreign or unknown id leaves the occasion untouched.
    people = await get_all_owned(session, Person, owner_id, person_ids)
    occasion.name = name
    occasion.date = date
    occasion.recurrence = recurrence
    occasion.occasion_type_id = occasion_type_id
    occasion.people = people
    await session.flush()
    await _reload_people(session, occasion)
    return occasion


async def _reload_people(session: AsyncSession, occasion: Occasion) -> None:
    """Load the links in the relationship's order, so a response matches a later read."""
    await session.refresh(occasion, ["people"])


async def delete_occasion(
    session: AsyncSession, owner_id: uuid.UUID, occasion_id: uuid.UUID
) -> None:
    """Delete the owner's occasion."""
    occasion = await _get_editable_occasion(session, owner_id, occasion_id)
    if await gifting_service.is_occasion_in_use(session, occasion.id):
        raise ConflictError("Occasion is used by a gifting")
    await session.delete(occasion)
    await session.flush()


async def _get_editable_occasion(
    session: AsyncSession, owner_id: uuid.UUID, occasion_id: uuid.UUID
) -> Occasion:
    """Return the owner's occasion, unless it is a rule occasion, which nobody can change."""
    occasion = await get_occasion(session, owner_id, occasion_id)
    if occasion.occasion_type_id in RULE_TYPES:
        raise ConflictError("A rule occasion cannot be changed or deleted")
    return occasion


async def create_rule_occasions(session: AsyncSession, owner_id: uuid.UUID) -> None:
    """Add the account's rule occasions Geburtstag, Weihnachten and Ostern, without a date."""
    session.add_all(
        Occasion(
            owner_id=owner_id,
            occasion_type_id=type_id,
            name=RULE_NAMES[rule],
            recurrence=Recurrence.YEARLY,
        )
        for type_id, rule in RULE_TYPES.items()
    )
    await session.flush()


def _in_year(day: dt.date, year: int) -> dt.date:
    """The same day in another year; 29 February becomes 28 February outside leap years."""
    if day.month == 2 and day.day == 29 and not calendar.isleap(year):
        return dt.date(year, 2, 28)
    return day.replace(year=year)


def next_occurrence(start: dt.date, recurrence: Recurrence, today: dt.date) -> dt.date | None:
    """Next date of an occasion from today on, today included; None if a one-off is past."""
    if start >= today:
        return start
    if recurrence is Recurrence.NONE:
        return None
    candidate = _in_year(start, today.year)
    if candidate < today:
        candidate = _in_year(start, today.year + 1)
    return candidate


def easter_sunday(year: int) -> dt.date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 19 * el) // 433
    month = (h + el - 7 * m + 90) // 25
    day = (h + el - 7 * m + 33 * month + 19) % 32
    return dt.date(year, month, day)


def rule_date(rule: OccasionRule, today: dt.date) -> dt.date | None:
    """Next date of a rule occasion from today on; None for the birthday, which has no date."""
    if rule is OccasionRule.BIRTHDAY:
        return None
    if rule is OccasionRule.CHRISTMAS:
        return next_occurrence(dt.date(today.year, 12, 24), Recurrence.YEARLY, today)
    easter = easter_sunday(today.year)
    return easter if easter >= today else easter_sunday(today.year + 1)
