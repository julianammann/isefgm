"""Labelled links on gift ideas (F-07). No HTTP in here.

Links are the rows of `attachment` with kind `link`; images (#29) share the table. An
attachment has no owner_id; this module scopes its queries through gift.owner_id.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Attachment

# TODO(F-07): Owner scope, used by every read below:
#   def _owned_links(owner_id) -> Select[tuple[Attachment]]:
#       select(Attachment).join(Gift, Gift.id == Attachment.gift_id)
#           .where(Gift.owner_id == owner_id, Attachment.kind == AttachmentKind.LINK)
#   The kind filter matters once #29 stores images: /links/{id} of an image must be 404
#   and the link list must not count images.


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
    # TODO(F-07): Like list_notes: optional gift_id filter, order_by(Attachment.id),
    #   paginate.
    raise NotImplementedError


async def get_link(session: AsyncSession, owner_id: uuid.UUID, link_id: uuid.UUID) -> Attachment:
    """Return the owner's link.

    Raises:
        NotFoundError: The link does not exist or belongs to another account.
    """
    # TODO(F-07): session.scalar(_owned_links(owner_id).where(Attachment.id == link_id));
    #   None -> raise NotFoundError("Link not found").
    raise NotImplementedError


async def create_link(
    session: AsyncSession, owner_id: uuid.UUID, *, gift_id: uuid.UUID, label: str, url: str
) -> Attachment:
    """Add a link to one of the owner's gift ideas.

    Raises:
        NotFoundError: The idea does not exist or belongs to another account.
    """
    # TODO(F-07): get_owned(session, Gift, owner_id, gift_id) first, then
    #   Attachment(gift_id=..., kind=AttachmentKind.LINK, label=..., url=...), add, flush.
    #   The URL is already checked by LinkIn.
    raise NotImplementedError


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
    # TODO(F-07): get_link, then get_owned(Gift, gift_id), then assign label, url, gift_id;
    #   flush. Never touch kind.
    raise NotImplementedError


async def delete_link(session: AsyncSession, owner_id: uuid.UUID, link_id: uuid.UUID) -> None:
    """Delete the owner's link."""
    # TODO(F-07): get_link, session.delete, session.flush.
    raise NotImplementedError
