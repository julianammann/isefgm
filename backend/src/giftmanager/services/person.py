"""People of an account (F-02). No HTTP in here."""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError
from giftmanager.models import Person


async def list_persons(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Person], int]:
    """Return one page of the owner's persons, sorted by name, and the total count."""
    total = await session.scalar(
        select(func.count()).select_from(Person).where(Person.owner_id == owner_id)
    )
    persons = await session.scalars(
        select(Person)
        .where(Person.owner_id == owner_id)
        .order_by(func.lower(Person.name), Person.id)
        .limit(limit)
        .offset(offset)
    )
    return list(persons), total or 0


async def get_person(session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID) -> Person:
    """Return the owner's person."""
    person = await session.scalar(
        select(Person).where(Person.id == person_id, Person.owner_id == owner_id)
    )
    if person is None:
        raise NotFoundError("Person not found")
    return person


async def create_person(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    name: str,
    birthday: date | None,
    relationship: str | None,
    notes: str | None,
) -> Person:
    """Create a person for the owner."""
    person = Person(
        owner_id=owner_id,
        name=name,
        birthday=birthday,
        relationship=relationship,
        notes=notes,
    )
    session.add(person)
    await session.flush()
    return person


async def update_person(
    session: AsyncSession,
    owner_id: uuid.UUID,
    person_id: uuid.UUID,
    *,
    name: str,
    birthday: date | None,
    relationship: str | None,
    notes: str | None,
) -> Person:
    """Replace all editable fields of the owner's person."""
    person = await get_person(session, owner_id, person_id)
    person.name = name
    person.birthday = birthday
    person.relationship = relationship
    person.notes = notes
    await session.flush()
    return person


async def delete_person(session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID) -> None:
    """Delete the owner's person."""
    person = await get_person(session, owner_id, person_id)
    await session.delete(person)
    await session.flush()
