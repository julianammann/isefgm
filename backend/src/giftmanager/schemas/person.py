"""Request and response bodies of the person endpoints (F-02)."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from giftmanager.schemas.common import OptionalLongText, blank_to_none

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
OptionalShortText = Annotated[ShortText | None, BeforeValidator(blank_to_none)]


class PersonIn(BaseModel):
    """Data of a person; used for create and for full update (PUT)."""

    name: Name = Field(description="Name, 1 to 100 characters.", examples=["Lena"])
    birthday: date | None = Field(
        default=None,
        description="Birthday as a plain date (YYYY-MM-DD), without time or time zone.",
        examples=["1994-03-17"],
    )
    relationship: OptionalShortText = Field(
        default=None,
        description="Relationship to the person, up to 100 characters. Empty means not set.",
        examples=["Schwester"],
    )
    notes: OptionalLongText = Field(
        default=None,
        description="Free-text notes, up to 2000 characters. Empty means not set.",
        examples=["Mag Bouldern und Kaffee, Kleidergröße M"],
    )


class PersonOut(BaseModel):
    """A person as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Person ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"]
    )
    name: str = Field(description="Name.", examples=["Lena"])
    birthday: date | None = Field(
        description="Birthday as a plain date, or null.", examples=["1994-03-17"]
    )
    relationship: str | None = Field(
        description="Relationship to the person, or null.", examples=["Schwester"]
    )
    notes: str | None = Field(
        description="Free-text notes, or null.",
        examples=["Mag Bouldern und Kaffee, Kleidergröße M"],
    )
    created_at: datetime = Field(
        description="Creation time (UTC).", examples=["2026-10-04T09:30:00Z"]
    )
