"""Labelled notes on gift ideas (F-07). No HTTP in here.

A note has no owner_id; it belongs to the account of its gift idea. Like services/gifting.py,
this module scopes its own queries through gift.owner_id; `paginate()` still applies.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Note

# TODO(F-07): Owner scope, used by every read below:
#   def _owned_notes(owner_id) -> Select[tuple[Note]]:
#       return select(Note).join(Gift, Gift.id == Note.gift_id).where(Gift.owner_id == owner_id)
#   (explicit ON clause: Note has no relationship to Gift.) Same join as _owned_giftings;
#   with the third copy in services/link.py a shared helper in ownership.py may pay off.


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
    # TODO(F-07): stmt = _owned_notes(owner_id); if gift_id: stmt.where(Note.gift_id == gift_id)
    #   order_by(Note.id): UUIDv7, so creation order (test_list_filters_by_idea_...).
    #   paginate(session, stmt, limit=limit, offset=offset).
    raise NotImplementedError


async def get_note(session: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    """Return the owner's note.

    Raises:
        NotFoundError: The note does not exist or belongs to another account.
    """
    # TODO(F-07): session.scalar(_owned_notes(owner_id).where(Note.id == note_id));
    #   None -> raise NotFoundError("Note not found").
    raise NotImplementedError


async def create_note(
    session: AsyncSession, owner_id: uuid.UUID, *, gift_id: uuid.UUID, label: str, text: str
) -> Note:
    """Add a note to one of the owner's gift ideas.

    Raises:
        NotFoundError: The idea does not exist or belongs to another account.
    """
    # TODO(F-07): await get_owned(session, Gift, owner_id, gift_id) first (Q-01, README
    #   rule 4), then Note(gift_id=..., label=..., text=...), add, flush.
    raise NotImplementedError


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
    # TODO(F-07): get_note, then get_owned(Gift, gift_id), and only then assign: a foreign
    #   idea must leave the note untouched (test_note_cannot_go_to_a_foreign_idea[PUT]).
    #   flush.
    raise NotImplementedError


async def delete_note(session: AsyncSession, owner_id: uuid.UUID, note_id: uuid.UUID) -> None:
    """Delete the owner's note."""
    # TODO(F-07): get_note, session.delete, session.flush.
    raise NotImplementedError
