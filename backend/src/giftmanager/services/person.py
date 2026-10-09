"""People of an account (F-02). No HTTP in here.

Every write keeps the person's birthday occasion in line with person.birthday (F-03, F-04).
"""

import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Person
from giftmanager.services.occasion import delete_birthday, sync_birthday
from giftmanager.services.ownership import get_owned, owned, paginate


async def list_people(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Person], int]:
    """Return one page of the owner's people, sorted by name, and the total count."""
    return await paginate(
        session,
        owned(Person, owner_id).order_by(func.lower(Person.name), Person.id),
        limit=limit,
        offset=offset,
    )


async def get_person(session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID) -> Person:
    """Return the owner's person."""
    return await get_owned(session, Person, owner_id, person_id)


async def create_person(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    name: str,
    birthday: date | None,
    relationship: str | None,
    notes: str | None,
) -> Person:
    """Create a person for the owner, with a birthday occasion if the birthday is known."""
    person = Person(
        owner_id=owner_id,
        name=name,
        birthday=birthday,
        relationship=relationship,
        notes=notes,
    )
    session.add(person)
    await session.flush()
    await sync_birthday(session, person)
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
    """Replace all editable fields of the owner's person; the birthday occasion follows."""
    person = await get_person(session, owner_id, person_id)
    person.name = name
    person.birthday = birthday
    person.relationship = relationship
    person.notes = notes
    await session.flush()
    await sync_birthday(session, person)
    return person


async def delete_person(session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID) -> None:
    """Delete the owner's person and their birthday occasion."""
    person = await get_person(session, owner_id, person_id)
    await delete_birthday(session, person)
    await session.delete(person)
    await session.flush()
