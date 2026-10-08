"""Gift ideas of an account (F-05)."""

import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.occasion import Occasion
from giftmanager.models.person import Person


class GiftCategory(enum.StrEnum):
    """Kind of gift; the aggregated feature for suggestions (F-16)."""

    BOOKS = "books"
    GAMES = "games"
    EXPERIENCE = "experience"
    CLOTHING = "clothing"
    TECH = "tech"
    FOOD = "food"
    HOME = "home"
    VOUCHER = "voucher"
    OTHER = "other"


def _category_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum values, not member names."""
    return [str(member.value) for member in enum_cls]


# Link tables (F-04) without an owner_id: both sides belong to the same account, which the
# service checks before linking (Q-01). The primary key covers lookups by gift_id.
gift_person = Table(
    "gift_person",
    Base.metadata,
    Column(
        "gift_id",
        Uuid(),
        ForeignKey("gift.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Gift idea. Deleting it deletes the link.",
    ),
    Column(
        "person_id",
        Uuid(),
        ForeignKey("person.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Possible recipient. Deleting the person deletes the link.",
    ),
    comment="Possible recipients of a gift idea (F-04), n:m. Deleting the idea or the person "
    "removes only the link. Actual recipients belong to a gifting (F-06).",
)

gift_occasion = Table(
    "gift_occasion",
    Base.metadata,
    Column(
        "gift_id",
        Uuid(),
        ForeignKey("gift.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Gift idea. Deleting it deletes the link.",
    ),
    Column(
        "occasion_id",
        Uuid(),
        ForeignKey("occasion.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Possible occasion. Deleting the occasion deletes the link.",
    ),
    comment="Possible occasions of a gift idea (F-04), n:m. Deleting the idea or the occasion "
    "removes only the link. The concrete occasion belongs to a gifting (F-06).",
)


class Gift(TimestampMixin, Base):
    """Gift idea (F-05): the reusable content of an idea. Owned by exactly one account (Q-01)."""

    __tablename__ = "gift"
    __table_args__ = (
        Index("ix_gift_owner_id_created_at", "owner_id", "created_at"),
        CheckConstraint("price_from >= 0 AND price_to >= 0", name="price_non_negative"),
        CheckConstraint("price_from <= price_to", name="price_range_ordered"),
        # A currency means nothing without a price, and a price nothing without a currency.
        CheckConstraint(
            "(currency IS NULL) = (price_from IS NULL AND price_to IS NULL)",
            name="currency_with_price",
        ),
        {
            "comment": "Gift idea of an account (F-05): the reusable content of an idea. "
            "Visible only to its owner (Q-01); deleted together with the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        comment="Account the gift idea belongs to. Deleted together with the account.",
    )
    title: Mapped[str] = mapped_column(
        String(200), comment="Short title, the only required field for quick capture."
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="Free-text description. Optional."
    )
    price_from: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), comment="Lower end of the price range in `currency`. Optional."
    )
    price_to: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), comment="Upper end of the price range in `currency`. Optional."
    )
    currency: Mapped[str | None] = mapped_column(
        String(3),
        comment="ISO 4217 code of the price range currency, e.g. EUR. Set exactly when a "
        "price is set.",
    )
    category: Mapped[GiftCategory] = mapped_column(
        Enum(
            GiftCategory,
            name="gift_category",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_category_values,
        ),
        default=GiftCategory.OTHER,
        server_default=GiftCategory.OTHER.value,
        comment="Kind of gift, feature for suggestions (F-16). `other` when not chosen.",
    )

    # selectin: an async session cannot lazy-load on attribute access, and one extra query
    # per page loads the links of every idea on it. Same order as the people and occasion lists.
    people: Mapped[list[Person]] = relationship(
        secondary=gift_person,
        order_by=lambda: [func.lower(Person.name), Person.id],
        lazy="selectin",
    )
    occasions: Mapped[list[Occasion]] = relationship(
        secondary=gift_occasion,
        order_by=lambda: [Occasion.date, func.lower(Occasion.name), Occasion.id],
        lazy="selectin",
    )
