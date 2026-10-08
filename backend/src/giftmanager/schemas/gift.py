"""Request and response bodies of the gift idea endpoints (F-04, F-05)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from giftmanager.models import GiftCategory
from giftmanager.schemas.common import OptionalLongText
from giftmanager.schemas.person import LinkedPerson


def _to_cents(value: Decimal) -> Decimal:
    """Store 20 as 20.00, so a response right after a write looks like a later read."""
    return value.quantize(Decimal("0.01"))


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
# Matches the Numeric(10, 2) column: at most 8 digits before and 2 after the point.
Price = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2), AfterValidator(_to_cents)]
Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class GiftIn(BaseModel):
    """Data of a gift idea; used for create and for full update (PUT)."""

    title: Title = Field(
        description="Title, 1 to 200 characters. The only required field.",
        examples=["Raspberry Pi"],
    )
    description: OptionalLongText = Field(
        default=None,
        description="Free-text description, up to 2000 characters. Empty means not set.",
        examples=["Technik, für IT-Begeisterte"],
    )
    price_from: Price | None = Field(
        default=None,
        description="Lower end of the price range in `currency`, at most 2 decimal places.",
        examples=["10.00"],
    )
    price_to: Price | None = Field(
        default=None,
        description="Upper end of the price range in `currency`, at most 2 decimal places. "
        "Must not be below `price_from`.",
        examples=["100.00"],
    )
    currency: Currency | None = Field(
        default=None,
        description="ISO 4217 code of the price range currency, three capital letters. "
        "EUR when a price is given without one; not stored without a price.",
        examples=["EUR"],
    )
    category: GiftCategory = Field(
        default=GiftCategory.OTHER,
        description="Kind of gift, used for suggestions (F-16). `other` when not chosen.",
        examples=["tech"],
    )
    person_ids: list[uuid.UUID] = Field(
        default_factory=list[uuid.UUID],
        max_length=100,
        description="IDs of the account's people the idea is meant for (possible recipients), "
        "up to 100. Replaces the current links; empty or left out means none.",
        examples=[["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"]],
    )
    occasion_ids: list[uuid.UUID] = Field(
        default_factory=list[uuid.UUID],
        max_length=100,
        description="IDs of the account's occasions the idea is meant for, up to 100. "
        "Replaces the current links; empty or left out means none.",
        examples=[["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a72"]],
    )

    @model_validator(mode="after")
    def check_price_range(self) -> Self:
        """Reject a price range whose lower end is above its upper end."""
        if (
            self.price_from is not None
            and self.price_to is not None
            and self.price_from > self.price_to
        ):
            raise ValueError("price_from must not be greater than price_to")
        return self

    @model_validator(mode="after")
    def currency_only_with_a_price(self) -> Self:
        """Keep the currency exactly when a price is set; EUR if the price has none."""
        if self.price_from is None and self.price_to is None:
            # The form sends its currency field even when both prices are empty.
            self.currency = None
        elif self.currency is None:
            self.currency = "EUR"
        return self


class LinkedOccasion(BaseModel):
    """An occasion a gift idea is linked to."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Occasion ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a72"]
    )
    name: str = Field(description="Title.", examples=["Weihnachten"])


class GiftOut(BaseModel):
    """A gift idea as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Gift idea ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"]
    )
    title: str = Field(description="Title.", examples=["Raspberry Pi"])
    description: str | None = Field(
        description="Free-text description, or null.", examples=["Technik, für IT-Begeisterte"]
    )
    price_from: Decimal | None = Field(
        description="Lower end of the price range in `currency`, as a string, or null.",
        examples=["10.00"],
    )
    price_to: Decimal | None = Field(
        description="Upper end of the price range in `currency`, as a string, or null.",
        examples=["100.00"],
    )
    currency: str | None = Field(
        description="ISO 4217 currency code, or null when no price is set.", examples=["EUR"]
    )
    category: GiftCategory = Field(description="Kind of gift.", examples=["tech"])
    people: list[LinkedPerson] = Field(
        description="People the idea is meant for (possible recipients), sorted by name.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71", "name": "Lena"}]],
    )
    occasions: list[LinkedOccasion] = Field(
        description="Occasions the idea is meant for, sorted by date.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a72", "name": "Weihnachten"}]],
    )
    created_at: datetime = Field(
        description="Creation time (UTC), set by the server.", examples=["2026-10-04T09:30:00Z"]
    )
