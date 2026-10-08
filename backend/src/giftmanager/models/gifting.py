"""Giftings: concrete uses of a gift idea, each with its own status (F-06)."""

import enum
import uuid

from sqlalchemy import Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin


class GiftingStatus(enum.StrEnum):
    """Progress of a gifting (F-06). Any status may follow any other, also back from `given`."""

    IDEA = "idea"
    PLANNED = "planned"
    ACQUIRED = "acquired"
    GIVEN = "given"


# TODO(F-06): Columns of the link table, modelled on gift_person in models/gift.py:
#   - gifting_id: Uuid, ForeignKey("gifting.id", ondelete="CASCADE"), primary_key=True
#   - person_id:  Uuid, ForeignKey("person.id", ondelete="CASCADE"), primary_key=True,
#                 index=True. Deleting a person only removes them as a recipient
#                 (test_deleting_a_recipient_removes_them_from_the_gifting).
#   Every column gets a comment= (backend/README.md, "Dokumentation").
gifting_person = Table(
    "gifting_person",
    Base.metadata,
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
    # TODO(F-06): __table_args__ = (...)
    #   - CheckConstraint(..., name="given_complete") -> ck_gifting_given_complete
    #     (docs/datenmodell.md): status <> 'given' OR (occasion_id IS NOT NULL AND
    #     occasion_date IS NOT NULL AND given_on IS NOT NULL). At least one recipient is
    #     checked by GiftingIn, not by the database.
    #   - {"comment": "..."} as the last element, like Gift.

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )

    # TODO(F-06): Columns. Comments in English, see Gift for the style.
    #   gift_id: Mapped[uuid.UUID]
    #       ForeignKey("gift.id", ondelete="CASCADE"), index=True.
    #       CASCADE only for deleting the account (F-17), which deletes the gift in the same
    #       statement. Through the API an idea with giftings is not deletable: delete_gift
    #       answers 409 (test_idea_with_giftings_cannot_be_deleted). RESTRICT here would
    #       make test_deleting_the_account_deletes_its_giftings fail.
    #   status: Mapped[GiftingStatus]
    #       Enum(GiftingStatus, name="gifting_status", native_enum=False, length=16,
    #       create_constraint=True, values_callable=...) like Gift.category, so the
    #       database stores `idea`, not `IDEA`. default + server_default IDEA.
    #   occasion_id: Mapped[uuid.UUID | None]
    #       ForeignKey("occasion.id", ondelete="CASCADE"), index=True.
    #       Same reasoning as gift_id: the API answers 409 when an occasion in use is
    #       deleted (directly or as a derived birthday), the cascade only runs for F-17.
    #   occasion_date: Mapped[dt.date | None]
    #       Date. Concrete date of the occasion, e.g. Christmas 2026 for a yearly
    #       occasion (Q-08: plain calendar date, no time zone).
    #   given_on: Mapped[dt.date | None]
    #       Date. Day the gift was given; set exactly when status is `given`.

    # TODO(F-06): Relationships, all lazy="selectin" (no lazy loading in async code):
    #   gift: Mapped[Gift] = relationship(lazy="selectin")
    #   occasion: Mapped[Occasion | None] = relationship(lazy="selectin")
    #   people: Mapped[list[Person]] = relationship(secondary=gifting_person, order_by=...
    #       same order as Gift.people, lazy="selectin")
    #   No back-reference on Gift or Occasion: without passive_deletes the ORM would set
    #   gift_id/occasion_id to NULL on delete instead of letting the 409 check decide.

    # TODO(F-06): models/__init__.py already exports the names. Generate the migration:
    #   mise run db (repo root), mise run migration -- "create gifting and gifting_person",
    #   read it, mise run migrate, mise run migrate:check.
