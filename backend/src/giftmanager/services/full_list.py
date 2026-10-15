"""The account's complete list of people, gift ideas and past gifts (F-15). No HTTP in here."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import (
    Attachment,
    AttachmentKind,
    Gift,
    Gifting,
    GiftingStatus,
    Note,
    Person,
    User,
)
from giftmanager.services.ownership import owned


@dataclass
class ListedGift:
    """A gift idea with its web links and notes."""

    gift: Gift
    links: list[Attachment]
    notes: list[Note]


@dataclass
class FullList:
    """Everything the account has: people, gift ideas and gifts already given."""

    owner_name: str
    people: list[Person]
    gifts: list[ListedGift]
    given: list[Gifting]


async def get_full_list(session: AsyncSession, owner_id: uuid.UUID) -> FullList:
    """Load the owner's people, gift ideas with links and notes, and given gifts."""
    owner_name = await session.scalar(select(User.display_name).where(User.id == owner_id))
    people = await session.scalars(
        owned(Person, owner_id).order_by(func.lower(Person.name), Person.id)
    )
    gifts = await session.scalars(owned(Gift, owner_id).order_by(func.lower(Gift.title), Gift.id))
    links = await session.scalars(
        select(Attachment)
        .join(Gift, Gift.id == Attachment.gift_id)
        .where(Gift.owner_id == owner_id, Attachment.kind == AttachmentKind.LINK)
        .order_by(Attachment.id)
    )
    notes = await session.scalars(
        select(Note)
        .join(Gift, Gift.id == Note.gift_id)
        .where(Gift.owner_id == owner_id)
        .order_by(Note.id)
    )
    given = await session.scalars(
        select(Gifting)
        .join(Gifting.gift)
        .where(Gift.owner_id == owner_id, Gifting.status == GiftingStatus.GIVEN)
        .order_by(Gifting.given_on.desc(), Gifting.id.desc())
    )
    links_by_gift: dict[uuid.UUID, list[Attachment]] = {}
    for link in links:
        links_by_gift.setdefault(link.gift_id, []).append(link)
    notes_by_gift: dict[uuid.UUID, list[Note]] = {}
    for note in notes:
        notes_by_gift.setdefault(note.gift_id, []).append(note)
    return FullList(
        owner_name=owner_name or "",
        people=list(people),
        gifts=[
            ListedGift(
                gift=gift,
                links=links_by_gift.get(gift.id, []),
                notes=notes_by_gift.get(gift.id, []),
            )
            for gift in gifts
        ],
        given=list(given),
    )
