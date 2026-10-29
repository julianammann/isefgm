"""Request and response bodies of the suggestion endpoints (F-16)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from giftmanager.models import GiftCategory, PriceBand, SuggestionStatus
from giftmanager.schemas.common import PageParams
from giftmanager.schemas.gift import Title


class SuggestionListParams(PageParams):
    """Pagination for the suggestion list, optionally narrowed to one person."""

    person_id: uuid.UUID | None = Field(
        default=None, description="Only the suggestions for this person."
    )


class SuggestionRequest(BaseModel):
    """Person to make new suggestions for."""

    person_id: uuid.UUID = Field(
        description="ID of the account's person the suggestions are for.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"],
    )


class SuggestionAccept(BaseModel):
    """Title of the gift idea an accepted suggestion becomes."""

    title: Title = Field(
        description="Title of the new gift idea, 1 to 200 characters. The frontend fills in "
        "its wording of the suggestion; the user may change it.",
        examples=["Erlebnis, 20 bis 50 €"],
    )


class SuggestionOut(BaseModel):
    """A suggestion as the frontend sees it. The frontend words it from the keys."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Suggestion ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a76"]
    )
    target_person_id: uuid.UUID = Field(
        description="ID of the person the suggestion is for.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"],
    )
    category: GiftCategory = Field(
        description="Suggested kind of gift, never `other`.", examples=["experience"]
    )
    price_band: PriceBand | None = Field(
        description="Suggested price band in EUR: `under_20` (below 20), `20_to_50` (20 to "
        "below 50), `50_to_100` (50 to below 100) or `over_100` (100 and more). Null if the "
        "ideas behind it have no price in EUR.",
        examples=["20_to_50"],
    )
    gift_count: int = Field(
        description="Number of gift ideas of other accounts with this category and price band "
        "when the suggestion was made.",
        examples=[42],
    )
    status: SuggestionStatus = Field(
        description="`open`, `accepted` or `dismissed`.", examples=["open"]
    )
    created_at: datetime = Field(
        description="Creation time (UTC), set by the server.", examples=["2026-10-26T09:30:00Z"]
    )
