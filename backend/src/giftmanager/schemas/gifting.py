"""Request and response bodies of the gifting endpoints (F-06)."""

import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from giftmanager.models import GiftingStatus
from giftmanager.schemas.gift import LinkedOccasion
from giftmanager.schemas.person import LinkedPerson


class GiftingIn(BaseModel):
    """Data of a gifting; used for create and for full update (PUT)."""

    gift_id: uuid.UUID = Field(
        description="ID of the account's gift idea this gifting uses. The idea's content is "
        "referenced, not copied.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    status: GiftingStatus = Field(
        default=GiftingStatus.IDEA,
        description="`idea`, `planned`, `acquired` or `given`; `idea` when left out. Any "
        "status may follow any other. `given` needs recipients, an occasion, its date and "
        "`given_on`, so a past gift can be recorded in one step.",
        examples=["planned"],
    )
    person_ids: list[uuid.UUID] = Field(
        default_factory=list[uuid.UUID],
        max_length=100,
        description="IDs of the account's people who receive the gift (actual recipients), "
        "up to 100. Several people share one joint gift. At least one for `given`. Replaces "
        "the current recipients; empty or left out means none.",
        examples=[["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"]],
    )
    occasion_id: uuid.UUID | None = Field(
        default=None,
        description="ID of the account's occasion the gift is for. Required for `given`.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a72"],
    )
    occasion_date: date | None = Field(
        default=None,
        description="Concrete date of the occasion as a plain date (YYYY-MM-DD), e.g. "
        "Christmas 2026 for a yearly occasion. Required for `given`.",
        examples=["2026-12-24"],
    )
    given_on: date | None = Field(
        default=None,
        description="Day the gift was given, as a plain date (YYYY-MM-DD). Required for "
        "`given`; not stored with any other status.",
        examples=["2026-12-24"],
    )

    @model_validator(mode="after")
    def check_given_complete(self) -> Self:
        """Reject a given gifting without recipients, occasion, occasion date or given date."""
        # TODO(F-06): If self.status is GIVEN and person_ids is empty or occasion_id,
        #   occasion_date or given_on is None: raise ValueError(...). A ValueError in a
        #   model validator becomes 422 with loc ["body"], like check_price_range in
        #   schemas/gift.py (test_given_gifting_must_be_complete).
        return self

    @model_validator(mode="after")
    def given_on_only_when_given(self) -> Self:
        """Keep `given_on` only for a given gifting."""
        # TODO(F-06): If self.status is not GIVEN: set self.given_on = None. The form sends
        #   its date field whatever the status, and going back from `given` must clear the
        #   date (test_given_on_is_only_stored_when_given,
        #   test_status_can_go_back_from_given). Same idea as currency_only_with_a_price.
        return self


class LinkedGift(BaseModel):
    """The gift idea a gifting uses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Gift idea ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"]
    )
    title: str = Field(description="Current title of the idea.", examples=["Raspberry Pi"])


class GiftingOut(BaseModel):
    """A gifting as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Gifting ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a73"]
    )
    gift: LinkedGift = Field(
        description="The gift idea this gifting uses.",
        examples=[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70", "title": "Raspberry Pi"}],
    )
    status: GiftingStatus = Field(description="Progress of the gifting.", examples=["planned"])
    people: list[LinkedPerson] = Field(
        description="Actual recipients, sorted by name.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71", "name": "Lena"}]],
    )
    occasion: LinkedOccasion | None = Field(
        description="Occasion the gift is for, or null.",
        examples=[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a72", "name": "Weihnachten"}],
    )
    occasion_date: date | None = Field(
        description="Concrete date of the occasion as a plain date, or null.",
        examples=["2026-12-24"],
    )
    given_on: date | None = Field(
        description="Day the gift was given as a plain date; null unless `given`.",
        examples=["2026-12-24"],
    )
    created_at: datetime = Field(
        description="Creation time (UTC), set by the server.", examples=["2026-10-04T09:30:00Z"]
    )
