"""Share links of an account and the read-only view behind a token (F-14). No HTTP in here."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import DomainError, NotFoundError
from giftmanager.core.security import hash_session_token, new_session_token
from giftmanager.models import (
    Attachment,
    AttachmentKind,
    Gift,
    Person,
    ShareLink,
    User,
    gift_person,
)
from giftmanager.services.ownership import get_all_owned, get_owned, owned, paginate


@dataclass
class SharedGift:
    """A shared gift idea with its web links."""

    gift: Gift
    links: list[Attachment]


@dataclass
class SharedPerson:
    """A shared person with the gift ideas meant for them."""

    person: Person
    gifts: list[SharedGift]


@dataclass
class SharedList:
    """Everything a valid share link shows."""

    owner_name: str
    expires_at: datetime | None
    people: list[SharedPerson]


async def list_share_links(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[ShareLink], int]:
    """Return one page of the owner's share links, newest first, and the total count."""
    return await paginate(
        session,
        owned(ShareLink, owner_id).order_by(ShareLink.created_at.desc(), ShareLink.id.desc()),
        limit=limit,
        offset=offset,
    )


async def get_share_link(
    session: AsyncSession, owner_id: uuid.UUID, share_link_id: uuid.UUID
) -> ShareLink:
    """Return the owner's share link."""
    return await get_owned(session, ShareLink, owner_id, share_link_id)


def _check_expiry(expires_at: datetime | None, now: datetime) -> None:
    """Reject an expiry time that is not in the future."""
    if expires_at is not None and expires_at <= now:
        raise DomainError("expires_at must lie in the future")


async def create_share_link(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    person_ids: list[uuid.UUID],
    expires_at: datetime | None,
    active: bool,
    now: datetime,
) -> tuple[ShareLink, str]:
    """Create a share link on some of the owner's people and return it with its token."""
    _check_expiry(expires_at, now)
    people = await get_all_owned(session, Person, owner_id, person_ids)
    token = new_session_token()
    share_link = ShareLink(
        owner_id=owner_id,
        token_hash=hash_session_token(token),
        active=active,
        expires_at=expires_at,
        people=people,
    )
    session.add(share_link)
    await session.flush()
    await session.refresh(share_link, ["people"])
    return share_link, token


async def update_share_link(
    session: AsyncSession,
    owner_id: uuid.UUID,
    share_link_id: uuid.UUID,
    *,
    person_ids: list[uuid.UUID],
    expires_at: datetime | None,
    active: bool,
    now: datetime,
) -> ShareLink:
    """Replace the people, expiry time and active flag of the owner's share link."""
    share_link = await get_share_link(session, owner_id, share_link_id)
    if expires_at != share_link.expires_at:
        _check_expiry(expires_at, now)
    people = await get_all_owned(session, Person, owner_id, person_ids)
    share_link.people = people
    share_link.expires_at = expires_at
    share_link.active = active
    await session.flush()
    await session.refresh(share_link, ["people"])
    return share_link


async def delete_share_link(
    session: AsyncSession, owner_id: uuid.UUID, share_link_id: uuid.UUID
) -> None:
    """Delete the owner's share link."""
    share_link = await get_share_link(session, owner_id, share_link_id)
    await session.delete(share_link)
    await session.flush()


async def open_share_link(session: AsyncSession, token: str, *, now: datetime) -> ShareLink:
    """Return the active, unexpired share link for a token."""
    share_link = await session.scalar(
        select(ShareLink).where(ShareLink.token_hash == hash_session_token(token))
    )
    if (
        share_link is None
        or not share_link.active
        or (share_link.expires_at is not None and share_link.expires_at <= now)
    ):
        raise NotFoundError("Share link not found")
    return share_link


async def get_shared_list(session: AsyncSession, token: str, *, now: datetime) -> SharedList:
    """Return the people of a valid share link with their gift ideas and web links."""
    share_link = await open_share_link(session, token, now=now)
    owner_name = await session.scalar(
        select(User.display_name).where(User.id == share_link.owner_id)
    )
    person_ids = [person.id for person in share_link.people]
    rows = (
        await session.execute(
            select(gift_person.c.person_id, Gift)
            .join(Gift, Gift.id == gift_person.c.gift_id)
            .where(
                gift_person.c.person_id.in_(person_ids),
                Gift.owner_id == share_link.owner_id,
            )
            .order_by(Gift.created_at.desc(), Gift.id.desc())
        )
    ).all()
    gift_ids = {gift.id for _, gift in rows}
    links = await session.scalars(
        select(Attachment)
        .where(Attachment.gift_id.in_(gift_ids), Attachment.kind == AttachmentKind.LINK)
        .order_by(Attachment.id)
    )
    links_by_gift: dict[uuid.UUID, list[Attachment]] = {}
    for link in links:
        links_by_gift.setdefault(link.gift_id, []).append(link)
    gifts_by_person: dict[uuid.UUID, list[SharedGift]] = {}
    for person_id, gift in rows:
        shared_gift = SharedGift(gift=gift, links=links_by_gift.get(gift.id, []))
        gifts_by_person.setdefault(person_id, []).append(shared_gift)
    return SharedList(
        owner_name=owner_name or "",
        expires_at=share_link.expires_at,
        people=[
            SharedPerson(person=person, gifts=gifts_by_person.get(person.id, []))
            for person in share_link.people
        ],
    )
