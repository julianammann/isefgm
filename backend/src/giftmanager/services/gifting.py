"""Giftings: concrete uses of a gift idea with their own status (F-06). No HTTP in here.

A gifting has no owner_id; it belongs to the account of its gift idea. The Q-01 helpers
`owned()` and `get_owned()` need an owner_id (Protocol `Owned`), so this module scopes its
own queries through gift.owner_id. `paginate()` and `get_all_owned()` still apply.
"""

import uuid
from datetime import date

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError, UnprocessableError
from giftmanager.models import (
    BIRTHDAY_TYPE_ID,
    Gift,
    Gifting,
    GiftingStatus,
    Occasion,
    Person,
)
from giftmanager.services.ownership import get_all_owned, get_owned, paginate


def _owned_giftings(owner_id: uuid.UUID) -> Select[tuple[Gifting]]:
    """Select giftings whose gift idea belongs to the given account."""
    return select(Gifting).join(Gifting.gift).where(Gift.owner_id == owner_id)


async def list_giftings(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Gifting], int]:
    """Return one page of the owner's giftings, newest first, and the total count."""
    statement = _owned_giftings(owner_id).order_by(
        Gifting.created_at.desc(),
        Gifting.id.desc(),
    )
    return await paginate(session, statement, limit=limit, offset=offset)


async def get_gifting(session: AsyncSession, owner_id: uuid.UUID, gifting_id: uuid.UUID) -> Gifting:
    """Return the owner's gifting.

    Raises:
        NotFoundError: The gifting does not exist or belongs to another account.
    """
    gifting = await session.scalar(_owned_giftings(owner_id).where(Gifting.id == gifting_id))
    if gifting is None:
        raise NotFoundError("Gifting not found")
    return gifting


def _check_birthday_recipient(occasion: Occasion | None, people: list[Person]) -> None:
    """A birthday gifting is for the person whose birthday it is: exactly one recipient."""
    if occasion is not None and occasion.occasion_type_id == BIRTHDAY_TYPE_ID and len(people) != 1:
        raise UnprocessableError("A birthday gifting needs exactly one recipient")


async def create_gifting(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    status: GiftingStatus,
    person_ids: list[uuid.UUID],
    occasion_id: uuid.UUID | None,
    occasion_date: date | None,
    given_on: date | None,
) -> Gifting:
    """Create a gifting of one of the owner's gift ideas, in one step (QZ-01).

    Raises:
        NotFoundError: The idea, a person or the occasion does not exist or belongs to
            another account.
        UnprocessableError: The occasion is Geburtstag and there is not exactly one recipient.
    """
    gift = await get_owned(session, Gift, owner_id, gift_id)
    people = await get_all_owned(session, Person, owner_id, person_ids)

    occasion = None
    if occasion_id is not None:
        occasion = await get_owned(session, Occasion, owner_id, occasion_id)
    _check_birthday_recipient(occasion, people)

    gifting = Gifting(
        gift=gift,
        status=status,
        people=people,
        occasion=occasion,
        occasion_date=occasion_date,
        given_on=given_on,
    )
    session.add(gifting)
    await session.flush()
    await session.refresh(gifting, ["people"])
    return gifting


async def update_gifting(
    session: AsyncSession,
    owner_id: uuid.UUID,
    gifting_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    status: GiftingStatus,
    person_ids: list[uuid.UUID],
    occasion_id: uuid.UUID | None,
    occasion_date: date | None,
    given_on: date | None,
) -> Gifting:
    """Replace all editable fields and recipients of the owner's gifting.

    Raises:
        NotFoundError: The gifting, the idea, a person or the occasion does not exist or
            belongs to another account.
        UnprocessableError: The occasion is Geburtstag and there is not exactly one recipient.
    """
    gifting = await get_gifting(session, owner_id, gifting_id)
    gift = await get_owned(session, Gift, owner_id, gift_id)
    people = await get_all_owned(session, Person, owner_id, person_ids)

    occasion = None
    if occasion_id is not None:
        occasion = await get_owned(session, Occasion, owner_id, occasion_id)
    _check_birthday_recipient(occasion, people)

    gifting.gift = gift
    gifting.status = status
    gifting.people = people
    gifting.occasion = occasion
    gifting.occasion_date = occasion_date
    gifting.given_on = given_on

    await session.flush()
    await session.refresh(gifting, ["people"])
    return gifting


async def delete_gifting(session: AsyncSession, owner_id: uuid.UUID, gifting_id: uuid.UUID) -> None:
    """Delete the owner's gifting and its tasks; the idea, people and occasion stay."""
    gifting = await get_gifting(session, owner_id, gifting_id)
    await session.delete(gifting)
    await session.flush()


async def is_gift_in_use(session: AsyncSession, gift_id: uuid.UUID) -> bool:
    """Return whether any gifting uses the gift idea."""

    # No owner filter needed: the caller already holds the owner's gift.
    # Used by delete_gift (services/gift.py) for the 409.
    statement = select(exists().where(Gifting.gift_id == gift_id))
    return bool(await session.scalar(statement))


async def is_occasion_in_use(session: AsyncSession, occasion_id: uuid.UUID) -> bool:
    """Return whether any gifting refers to the occasion."""

    # Used by delete_occasion (services/occasion.py).
    statement = select(exists().where(Gifting.occasion_id == occasion_id))
    return bool(await session.scalar(statement))
