"""Giftings: concrete uses of a gift idea, each with its own status (F-06)."""

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Table,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.gift import Gift
from giftmanager.models.occasion import Occasion
from giftmanager.models.person import Person


class GiftingStatus(enum.StrEnum):
    """Progress of a gifting (F-06). Any status may follow any other, also back from `given`."""

    IDEA = "idea"
    PLANNED = "planned"
    ACQUIRED = "acquired"
    GIVEN = "given"


def _status_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum value, not member names."""
    return [str(member.value) for member in enum_cls]


gifting_person = Table(
    "gifting_person",
    Base.metadata,
    Column(
        "gifting_id",
        Uuid(),
        ForeignKey("gifting.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Gifting. Deleting it deletes the link.",
    ),
    Column(
        "person_id",
        Uuid(),
        ForeignKey("person.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Actual recipient. Deleting a person only removes them as a recipient, the gifting remains "
        "(test_deleting_a_recipient_removes_them_from_the_gifting).",
    ),
    comment="Actual recipients of a gifting (F-06), n:m. Several people share one joint gift. "
    "Deleting the gifting or the person removes only the link.",
)


class Gifting(TimestampMixin, Base):
    """One concrete use of a gift idea (F-06): status, recipients, occasion and dates.

    There is no owner_id: a gifting belongs to the account of its gift idea, so every query
    scopes through gift.owner_id (services/gifting.py). The idea's content is referenced,
    never copied, so turning an idea into a gifting is one step (QZ-01).
    """

    __tablename__ = "gifting"
    __table_args__ = (
        CheckConstraint(
            "status <> 'given' OR "
            "(occasion_id IS NOT NULL AND occasion_date IS NOT NULL AND given_on IS NOT NULL)",
            name="given_complete",
        ),
        {
            "comment": "Concrete use of a gift idea (F-06), with its own status, actual recipients, "
            "occasion and dates. Belongs to the account of the gift idea; deleted together with "
            "the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    gift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gift.id", ondelete="CASCADE"),
        index=True,
        comment="CASCADE only for deleting the account (F-17), which deletes the gift in the same statement. "
        "Through the API an idea with giftings is not deletable: delete_gift answers 409 "
        "(test_idea_with_giftings_cannot_be_deleted). "
        "RESTRICT here would make test_deleting_the_account_deletes_its_giftings fail.",
    )
    status: Mapped[GiftingStatus] = mapped_column(
        Enum(
            GiftingStatus,
            name="gifting_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_status_values,
        ),
        default=GiftingStatus.IDEA,
        server_default=GiftingStatus.IDEA.value,
        comment="Progress of the gifting. Defaults to 'idea'.",
    )
    occasion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occasion.id", ondelete="CASCADE"),
        index=True,
        comment="Same reasoning as gift_id: the API answers 409 when an occasion in use is "
        "deleted, the cascade only runs for F-17.",
    )
    occasion_date: Mapped[dt.date | None] = mapped_column(
        comment="Date. Concrete date of the occasion, e.g. Christmas 2026 for a yearly "
        "occasion (Q-08: plain calendar date, no time zone).",
    )
    given_on: Mapped[dt.date | None] = mapped_column(
        comment="Date. Day the gift was given; set exactly when status is `given`.",
    )

    # Relationships, all lazy="selectin" (no lazy loading in async code).
    # No back-reference on Gift or Occasion: without passive_deletes the ORM would set
    # gift_id/occasion_id to NULL on delete instead of letting the 409 check decide.
    gift: Mapped[Gift] = relationship(
        lazy="selectin",
    )
    occasion: Mapped[Occasion | None] = relationship(
        lazy="selectin",
    )
    people: Mapped[list[Person]] = relationship(
        secondary=gifting_person,
        order_by=lambda: [func.lower(Person.name), Person.id],
        lazy="selectin",
    )
