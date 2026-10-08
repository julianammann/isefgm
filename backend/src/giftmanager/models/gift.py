"""Gift ideas of an account (F-05)."""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin


class Gift(TimestampMixin, Base):
    """Gift idea (F-05): the reusable content of an idea. Owned by exactly one account (Q-01)."""

    __tablename__ = "gift"
    __table_args__ = (
        Index("ix_gift_owner_id_created_at", "owner_id", "created_at"),
        CheckConstraint("price_from >= 0 AND price_to >= 0", name="price_non_negative"),
        CheckConstraint("price_from <= price_to", name="price_range_ordered"),
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
        Numeric(10, 2), comment="Lower end of the price range in euros. Optional."
    )
    price_to: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), comment="Upper end of the price range in euros. Optional."
    )
