"""The person view (F-09): what a person got, what they may get and what is left to do.

No HTTP in here. Every list is one page; relations are loaded per page, never per row (QZ-02).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gift, Gifting, GiftingStatus, Occasion, Person, Task
from giftmanager.services.ownership import get_owned, owned, paginate


@dataclass
class PersonOverview:
    """One page of each list of the person view with its total, and the tasks of its giftings."""

    given: tuple[list[Gifting], int]
    giftings: tuple[list[Gifting], int]
    ideas: tuple[list[Gift], int]
    occasions: tuple[list[Occasion], int]
    tasks: dict[uuid.UUID, list[Task]]


async def get_person_overview(
    session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID, *, limit: int, offset: int
) -> PersonOverview:
    """Load the person view of the owner's person in a fixed number of queries.

    Raises:
        NotFoundError: The person does not exist or belongs to another account.
    """
    await get_owned(session, Person, owner_id, person_id)
    received = (
        select(Gifting)
        .join(Gifting.gift)
        .where(Gift.owner_id == owner_id, Gifting.people.any(Person.id == person_id))
    )
    given = await paginate(
        session,
        received.where(Gifting.status == GiftingStatus.GIVEN).order_by(
            Gifting.given_on.desc(), Gifting.id.desc()
        ),
        limit=limit,
        offset=offset,
    )
    giftings = await paginate(
        session,
        received.where(Gifting.status != GiftingStatus.GIVEN).order_by(
            Gifting.occasion_date.asc().nulls_last(), Gifting.created_at.desc(), Gifting.id.desc()
        ),
        limit=limit,
        offset=offset,
    )
    # An idea already used for the person shows up as their gifting instead (MS 1, data rules).
    used = select(Gifting.gift_id).where(Gifting.people.any(Person.id == person_id))
    ideas = await paginate(
        session,
        owned(Gift, owner_id)
        .where(Gift.people.any(Person.id == person_id), Gift.id.not_in(used))
        .order_by(Gift.created_at.desc(), Gift.id.desc()),
        limit=limit,
        offset=offset,
    )
    occasions = await paginate(
        session,
        owned(Occasion, owner_id)
        .where(Occasion.people.any(Person.id == person_id))
        .order_by(Occasion.date, func.lower(Occasion.name), Occasion.id),
        limit=limit,
        offset=offset,
    )
    tasks = await session.scalars(
        select(Task)
        .where(Task.gifting_id.in_([gifting.id for gifting in given[0] + giftings[0]]))
        .order_by(Task.due_on.asc().nulls_last(), Task.id)
    )
    tasks_by_gifting: dict[uuid.UUID, list[Task]] = {}
    for task in tasks:
        tasks_by_gifting.setdefault(task.gifting_id, []).append(task)
    return PersonOverview(
        given=given, giftings=giftings, ideas=ideas, occasions=occasions, tasks=tasks_by_gifting
    )
