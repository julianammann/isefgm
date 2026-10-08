"""Request and response bodies of the occasion type and occasion endpoints (F-03)."""

import datetime as dt
import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from giftmanager.models import Recurrence
from giftmanager.schemas.person import LinkedPerson

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class OccasionTypeOut(BaseModel):
    """An occasion type. System-wide types are read-only."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Occasion type ID (UUIDv7).", examples=["01a107a9-211b-7486-a304-d5d673618f5b"]
    )
    name: str = Field(description="Display name.", examples=["Geburtstag"])
    default_recurrence: Recurrence = Field(
        description="Suggested recurrence for occasions of this type.", examples=["yearly"]
    )
    system: bool = Field(
        description="True for the system-wide types, which nobody can change or delete.",
        examples=[True],
    )


class OccasionIn(BaseModel):
    """Data of an occasion; used for create and for full update (PUT)."""

    name: Name = Field(description="Title, 1 to 100 characters.", examples=["Hochzeitstag"])
    date: dt.date = Field(
        description="Date as a plain date (YYYY-MM-DD). First occurrence for yearly occasions.",
        examples=["2019-06-21"],
    )
    recurrence: Recurrence = Field(
        default=Recurrence.NONE,
        description="`none` for a one-off occasion, `yearly` for every year on the same day.",
        examples=["yearly"],
    )
    occasion_type_id: uuid.UUID | None = Field(
        default=None,
        description="Occasion type, a system-wide one or one of the account. Null for an own "
        "occasion without a type.",
        examples=[None],
    )
    person_ids: list[uuid.UUID] = Field(
        default_factory=list[uuid.UUID],
        max_length=100,
        description="IDs of the account's people the occasion concerns, up to 100. Replaces "
        "the current links; empty or left out means none.",
        examples=[["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"]],
    )


class OccasionOut(BaseModel):
    """An occasion as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Occasion ID (UUIDv7).", examples=["01a10a3c-7d2e-7c41-9b0e-3f5a8d2c1e94"]
    )
    name: str = Field(description="Title.", examples=["Hochzeitstag"])
    date: dt.date = Field(description="Date as a plain date.", examples=["2019-06-21"])
    recurrence: Recurrence = Field(description="`none` or `yearly`.", examples=["yearly"])
    occasion_type_id: uuid.UUID | None = Field(
        description="Occasion type, or null.", examples=[None]
    )
    people: list[LinkedPerson] = Field(
        description="People the occasion concerns, sorted by name.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71", "name": "Lena"}]],
    )
