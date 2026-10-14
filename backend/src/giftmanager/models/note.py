"""Labelled notes on a gift idea (F-07)."""

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base


class Note(Base):
    """Labelled note on a gift idea (F-07), e.g. label "Größe", text "M, eher weit".

    There is no owner_id: a note belongs to the account of its gift idea, so every query
    scopes through gift.owner_id (services/note.py), like a gifting.
    """

    __tablename__ = "note"
    __table_args__ = (
        {
            "comment": "Labelled note on a gift idea (F-07). Visible only to the owner of the "
            "idea (Q-01); deleted together with the idea and the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key, UUIDv7. Also the list order: oldest note first.",
    )
    gift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gift.id", ondelete="CASCADE"),
        index=True,
        comment="Gift idea the note belongs to. Deleting the idea deletes the note.",
    )
    label: Mapped[str] = mapped_column(String(100), comment="Label, e.g. Größe.")
    text: Mapped[str] = mapped_column(Text, comment="Text of the note, up to 2000 characters.")
