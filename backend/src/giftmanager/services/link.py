"""Labelled links on gift ideas (F-07). No HTTP in here.

Links are the rows of `attachment` with kind `link`; images (#29) share the table. An
attachment has no owner_id; this module scopes its queries through gift.owner_id.
"""

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError
from giftmanager.models import Attachment, AttachmentKind, Gift
from giftmanager.services.ownership import get_owned, paginate


def _owned_links(owner_id: uuid.UUID) -> Select[tuple[Attachment]]:
    """Select links whose gift idea belongs to the given account; images are left out."""
    return (
        select(Attachment)
        .join(Gift, Gift.id == Attachment.gift_id)
        .where(Gift.owner_id == owner_id, Attachment.kind == AttachmentKind.LINK)
    )


async def list_links(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gift_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Attachment], int]:
    """Return one page of the owner's links, oldest first, and the total count.

    With `gift_id`, only the links of that idea; an idea of another account yields an
    empty page.
    """
    statement = _owned_links(owner_id)
    if gift_id is not None:
        statement = statement.where(Attachment.gift_id == gift_id)
    return await paginate(session, statement.order_by(Attachment.id), limit=limit, offset=offset)


async def get_link(session: AsyncSession, owner_id: uuid.UUID, link_id: uuid.UUID) -> Attachment:
    """Return the owner's link.

    Raises:
        NotFoundError: The link does not exist or belongs to another account.
    """
    link = await session.scalar(_owned_links(owner_id).where(Attachment.id == link_id))
    if link is None:
        raise NotFoundError("Link not found")
    return link


async def create_link(
    session: AsyncSession, owner_id: uuid.UUID, *, gift_id: uuid.UUID, label: str, url: str
) -> Attachment:
    """Add a link to one of the owner's gift ideas.

    Raises:
        NotFoundError: The idea does not exist or belongs to another account.
    """
    await get_owned(session, Gift, owner_id, gift_id)
    link = Attachment(gift_id=gift_id, kind=AttachmentKind.LINK, label=label, url=url)
    session.add(link)
    await session.flush()
    return link


async def update_link(
    session: AsyncSession,
    owner_id: uuid.UUID,
    link_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    label: str,
    url: str,
) -> Attachment:
    """Replace all editable fields of the owner's link.

    Raises:
        NotFoundError: The link or the idea does not exist or belongs to another account.
    """
    link = await get_link(session, owner_id, link_id)
    await get_owned(session, Gift, owner_id, gift_id)
    link.gift_id = gift_id
    link.label = label
    link.url = url
    await session.flush()
    return link


async def delete_link(session: AsyncSession, owner_id: uuid.UUID, link_id: uuid.UUID) -> None:
    """Delete the owner's link."""
    link = await get_link(session, owner_id, link_id)
    await session.delete(link)
    await session.flush()
