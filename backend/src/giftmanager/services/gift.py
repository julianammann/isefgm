"""Gift ideas of an account (F-05) and their links to people and occasions (F-04).

No HTTP in here.
"""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gift, GiftCategory, Occasion, Person
from giftmanager.services.ownership import get_all_owned, get_owned, owned, paginate


async def list_gifts(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Gift], int]:
    """Return one page of the owner's gift ideas, newest first, and the total count."""
    # created_at is the transaction start, so ideas saved in one transaction tie;
    # the time-ordered UUIDv7 breaks the tie in creation order.
    return await paginate(
        session,
        owned(Gift, owner_id).order_by(Gift.created_at.desc(), Gift.id.desc()),
        limit=limit,
        offset=offset,
    )


async def get_gift(session: AsyncSession, owner_id: uuid.UUID, gift_id: uuid.UUID) -> Gift:
    """Return the owner's gift idea."""
    return await get_owned(session, Gift, owner_id, gift_id)


async def create_gift(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    title: str,
    description: str | None,
    price_from: Decimal | None,
    price_to: Decimal | None,
    currency: str | None,
    category: GiftCategory,
    person_ids: list[uuid.UUID],
    occasion_ids: list[uuid.UUID],
) -> Gift:
    """Create a gift idea for the owner, linked to some of the owner's people and occasions."""
    gift = Gift(
        owner_id=owner_id,
        title=title,
        description=description,
        price_from=price_from,
        price_to=price_to,
        currency=currency,
        category=category,
        people=await get_all_owned(session, Person, owner_id, person_ids),
        occasions=await get_all_owned(session, Occasion, owner_id, occasion_ids),
    )
    session.add(gift)
    await session.flush()
    await _reload_links(session, gift)
    return gift


async def update_gift(
    session: AsyncSession,
    owner_id: uuid.UUID,
    gift_id: uuid.UUID,
    *,
    title: str,
    description: str | None,
    price_from: Decimal | None,
    price_to: Decimal | None,
    currency: str | None,
    category: GiftCategory,
    person_ids: list[uuid.UUID],
    occasion_ids: list[uuid.UUID],
) -> Gift:
    """Replace all editable fields and links of the owner's gift idea."""
    gift = await get_gift(session, owner_id, gift_id)
    # Resolve the links first, so a foreign or unknown id leaves the idea untouched.
    people = await get_all_owned(session, Person, owner_id, person_ids)
    occasions = await get_all_owned(session, Occasion, owner_id, occasion_ids)
    gift.title = title
    gift.description = description
    gift.price_from = price_from
    gift.price_to = price_to
    gift.currency = currency
    gift.category = category
    gift.people = people
    gift.occasions = occasions
    await session.flush()
    await _reload_links(session, gift)
    return gift


async def _reload_links(session: AsyncSession, gift: Gift) -> None:
    """Load the links in the relationship's order, so a response matches a later read."""
    await session.refresh(gift, ["people", "occasions"])


async def delete_gift(session: AsyncSession, owner_id: uuid.UUID, gift_id: uuid.UUID) -> None:
    """Delete the owner's gift idea."""
    gift = await get_gift(session, owner_id, gift_id)
    await session.delete(gift)
    await session.flush()
