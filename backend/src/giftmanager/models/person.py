"""People the account owner gives gifts to (F-02)."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin


class Person(TimestampMixin, Base):
    """Gift recipient (F-02). Owned by exactly one account (Q-01)."""

    __tablename__ = "person"
    __table_args__ = (
        Index("ix_person_owner_id_birthday", "owner_id", "birthday"),
        {
            "comment": "Person the account owner gives gifts to (F-02). Visible only to its "
            "owner (Q-01); deleted together with the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        comment="Account the person belongs to. Deleted together with the account.",
    )
    name: Mapped[str] = mapped_column(String(100), comment="Name as the owner calls the person.")
    birthday: Mapped[date | None] = mapped_column(
        Date, comment="Birthday as a plain date, optional. Source for birthday reminders."
    )
    relationship: Mapped[str | None] = mapped_column(
        String(100), comment="Free-text relationship, e.g. sister or colleague. Optional."
    )
    notes: Mapped[str | None] = mapped_column(
        Text, comment="Free-text notes, e.g. hobbies or sizes. Optional."
    )
