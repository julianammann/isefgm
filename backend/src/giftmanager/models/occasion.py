"""Occasion types and occasions (F-03)."""

import datetime as dt
import enum
import uuid

from sqlalchemy import Column, Date, Enum, ForeignKey, String, Table, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from giftmanager.models.base import Base
from giftmanager.models.person import Person

BIRTHDAY_TYPE_ID = uuid.UUID("01a107a9-211b-7486-a304-d5d673618f5b")
CHRISTMAS_TYPE_ID = uuid.UUID("01a107a9-211b-7486-a304-d5d72f070565")


class Recurrence(enum.StrEnum):
    """How often an occasion repeats."""

    NONE = "none"
    YEARLY = "yearly"


def _recurrence_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum values, not member names."""
    return [str(member.value) for member in enum_cls]


def _recurrence_column(name: str) -> Enum:
    """Text column limited to the recurrence values by a CHECK constraint."""
    return Enum(
        Recurrence,
        name=name,
        native_enum=False,
        length=16,
        create_constraint=True,
        values_callable=_recurrence_values,
    )


class OccasionType(Base):
    """Kind of occasion (F-03). System-wide types have no owner and cannot be changed."""

    __tablename__ = "occasion_type"
    __table_args__ = (
        {
            "comment": "Kind of occasion (F-03). owner_id NULL marks the system-wide types "
            "Geburtstag and Weihnachten, created by a migration and read-only for users."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account that defined the type. NULL for system-wide types.",
    )
    name: Mapped[str] = mapped_column(String(100), comment="Display name, e.g. Geburtstag.")
    default_recurrence: Mapped[Recurrence] = mapped_column(
        _recurrence_column("occasion_type_recurrence"),
        default=Recurrence.YEARLY,
        server_default=Recurrence.YEARLY.value,
        comment="`none` or `yearly`. Suggested recurrence for occasions of this type.",
    )


# Link table (F-04) without an owner_id: both sides belong to the same account, which the
# service checks before linking (Q-01). The primary key covers lookups by person_id.
person_occasion = Table(
    "person_occasion",
    Base.metadata,
    Column(
        "person_id",
        Uuid(),
        ForeignKey("person.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Person the occasion concerns. Deleting the person deletes the link.",
    ),
    Column(
        "occasion_id",
        Uuid(),
        ForeignKey("occasion.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Occasion. Deleting it deletes the link.",
    ),
    comment="People an occasion concerns (F-04), n:m. Deleting the person or the occasion "
    "removes only the link.",
)


class Occasion(Base):
    """Occasion of an account (F-03), one-off or yearly."""

    __tablename__ = "occasion"
    __table_args__ = (
        {
            "comment": "Occasion of an account (F-03). Stores the rule (date and recurrence); "
            "a concrete year is stored where the occasion is used. Visible only to its "
            "owner (Q-01)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account the occasion belongs to. Deleted together with the account.",
    )
    occasion_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occasion_type.id"),
        index=True,
        comment="Type of the occasion. NULL for an own occasion without a type.",
    )
    name: Mapped[str] = mapped_column(String(100), comment="Title, e.g. Hochzeitstag.")
    date: Mapped[dt.date] = mapped_column(
        Date, comment="Date as a plain calendar date (Q-08). First occurrence for yearly ones."
    )
    recurrence: Mapped[Recurrence] = mapped_column(
        _recurrence_column("occasion_recurrence"),
        comment="`none` (once) or `yearly` (every year on the same day).",
    )

    # selectin as on Gift: no lazy loading in async code, one extra query per page.
    # Same order as the people list.
    people: Mapped[list[Person]] = relationship(
        secondary=person_occasion,
        order_by=lambda: [func.lower(Person.name), Person.id],
        lazy="selectin",
    )
