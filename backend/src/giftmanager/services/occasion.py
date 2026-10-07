"""Occasion types and occasions of an account (F-03). No HTTP in here."""

import calendar
import datetime as dt
import uuid

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError
from giftmanager.models import Occasion, OccasionType, Recurrence
from giftmanager.services.ownership import get_owned, owned, paginate


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
    """Return one page of the owner's occasions, sorted by date, and the total count."""
    return await paginate(
        session,
        owned(Occasion, owner_id).order_by(Occasion.date, func.lower(Occasion.name), Occasion.id),
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
) -> Occasion:
    """Create an occasion for the owner."""
    if occasion_type_id is not None:
        await get_occasion_type(session, owner_id, occasion_type_id)
    occasion = Occasion(
        owner_id=owner_id,
        name=name,
        date=date,
        recurrence=recurrence,
        occasion_type_id=occasion_type_id,
    )
    session.add(occasion)
    await session.flush()
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
) -> Occasion:
    """Replace all editable fields of the owner's occasion."""
    occasion = await get_occasion(session, owner_id, occasion_id)
    if occasion_type_id is not None:
        await get_occasion_type(session, owner_id, occasion_type_id)
    occasion.name = name
    occasion.date = date
    occasion.recurrence = recurrence
    occasion.occasion_type_id = occasion_type_id
    await session.flush()
    return occasion


async def delete_occasion(
    session: AsyncSession, owner_id: uuid.UUID, occasion_id: uuid.UUID
) -> None:
    """Delete the owner's occasion."""
    occasion = await get_occasion(session, owner_id, occasion_id)
    await session.delete(occasion)
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
