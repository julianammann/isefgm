"""Labelled notes on gift ideas (F-07). No HTTP in here.

A note has no owner_id; it belongs to the account of its gift idea. Like services/gifting.py,
this module scopes its own queries through gift.owner_id; `paginate()` still applies.
"""

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import NotFoundError
from giftmanager.models import Gift, Note
from giftmanager.services.ownership import get_owned, paginate


def _owned_notes(owner_id: uuid.UUID) -> Select[tuple[Note]]:
    """Select notes whose gift idea belongs to the given account."""
    return select(Note).join(Gift, Gift.id == Note.gift_id).where(Gift.owner_id == owner_id)


async def list_notes(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gift_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Note], int]:
    """Return one page of the owner's notes, oldest first, and the total count.

    With `gift_id`, only the notes of that idea. An idea of another account yields an empty
    page, not 404: the filter only narrows the owner's notes.
    """
    statement = _owned_notes(owner_id)
    if gift_id is not None:
        statement = statement.where(Note.gift_id == gift_id)
    return await paginate(session, statement.order_by(Note.id), limit=limit, offset=offset)


async def get_note(session: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    """Return the owner's note.

    Raises:
        NotFoundError: The note does not exist or belongs to another account.
    """
    note = await session.scalar(_owned_notes(owner_id).where(Note.id == note_id))
    if note is None:
        raise NotFoundError("Note not found")
    return note


async def create_note(
    session: AsyncSession, owner_id: uuid.UUID, *, gift_id: uuid.UUID, label: str, text: str
) -> Note:
    """Add a note to one of the owner's gift ideas.

    Raises:
        NotFoundError: The idea does not exist or belongs to another account.
    """
    await get_owned(session, Gift, owner_id, gift_id)
    note = Note(gift_id=gift_id, label=label, text=text)
    session.add(note)
    await session.flush()
    return note


async def update_note(
    session: AsyncSession,
    owner_id: uuid.UUID,
    note_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    label: str,
    text: str,
) -> Note:
    """Replace all editable fields of the owner's note.

    Raises:
        NotFoundError: The note or the idea does not exist or belongs to another account.
    """
    note = await get_note(session, owner_id, note_id)
    await get_owned(session, Gift, owner_id, gift_id)
    note.gift_id = gift_id
    note.label = label
    note.text = text
    await session.flush()
    return note


async def delete_note(session: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> None:
    """Delete the owner's note."""
    note = await get_note(session, owner_id, note_id)
    await session.delete(note)
    await session.flush()
