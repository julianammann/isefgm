"""Gift suggestions for a person (F-16), built from aggregated features only (Q-04)."""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.gift import GiftCategory


class PriceBand(enum.StrEnum):
    """Price band in EUR (F-16) of the lower price; each band excludes its upper bound."""

    UNDER_20 = "under_20"
    FROM_20_TO_50 = "20_to_50"
    FROM_50_TO_100 = "50_to_100"
    OVER_100 = "over_100"


class SuggestionStatus(enum.StrEnum):
    """State of a suggestion (F-16). Only `open` ones can be accepted or dismissed."""

    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum values, not member names."""
    return [str(member.value) for member in enum_cls]


class Suggestion(TimestampMixin, Base):
    """Suggested category and price band for one person of the account (F-16, Q-01, Q-04)."""

    __tablename__ = "suggestion"
    __table_args__ = (
        {
            "comment": "Suggested kind of gift for a person (F-16): category and price band "
            "aggregated over the gift ideas of other accounts, no titles or texts (Q-04). "
            "Visible only to its owner (Q-01); deleted together with the person and the "
            "account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account the suggestion belongs to. Deleted together with the account.",
    )
    target_person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"),
        index=True,
        comment="Person the suggestion is for. Deleting the person deletes the suggestion.",
    )
    category: Mapped[GiftCategory] = mapped_column(
        Enum(
            GiftCategory,
            name="gift_category",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        comment="Suggested kind of gift, never `other`.",
    )
    price_band: Mapped[PriceBand | None] = mapped_column(
        Enum(
            PriceBand,
            name="price_band",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        comment="Suggested price band in EUR. Null for ideas without a price in EUR.",
    )
    gift_count: Mapped[int] = mapped_column(
        Integer,
        comment="Number of gift ideas of other accounts with this category and price band when "
        "the suggestion was made. A count only, no reference to the ideas.",
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(
            SuggestionStatus,
            name="suggestion_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        default=SuggestionStatus.OPEN,
        server_default=SuggestionStatus.OPEN.value,
        comment="`open`, `accepted` or `dismissed`. A dismissed suggestion is never made "
        "again for the person.",
    )
