"""Labelled notes on a gift idea (F-07)."""

import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base


class Note(Base):
    """Labelled note on a gift idea (F-07), e.g. label "Größe", text "M, eher weit".

    There is no owner_id: a note belongs to the account of its gift idea, so every query
    scopes through gift.owner_id (services/note.py), like a gifting.
    """

    __tablename__ = "note"
    # TODO(F-07): __table_args__ = ({"comment": "..."},) like Gift: a labelled note of a gift
    #   idea, visible only to the idea's owner (Q-01), deleted with the idea.

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key, UUIDv7. Also the list order: oldest note first.",
    )

    # TODO(F-07): Columns, each with comment=:
    #   gift_id: Mapped[uuid.UUID]
    #       ForeignKey("gift.id", ondelete="CASCADE"), index=True. A note is part of the
    #       idea: deleting the idea or the account deletes it
    #       (test_deleting_the_idea_deletes_its_notes, ..._account_deletes_its_notes).
    #   label: Mapped[str]
    #       String(100). Required, NoteIn checks 1 to 100 characters.
    #   text: Mapped[str]
    #       Text. Required, NoteIn limits it to 2000 characters like Gift.description.
    #   No created_at in docs/datenmodell.md; the UUIDv7 id gives the creation order.
    #   No relationship needed: NoteOut returns gift_id, not the idea.

    # TODO(F-07): Migration only after the F-06 one exists (branch 27, merged into this one):
    #   otherwise autogenerate puts gifting, note and attachment into one file.
    #   mise run migration -- "create note and attachment", read it, migrate, migrate:check.
