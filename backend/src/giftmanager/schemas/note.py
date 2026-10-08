"""Request and response bodies of the note endpoints (F-07)."""

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from giftmanager.schemas.common import Label

NoteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class NoteIn(BaseModel):
    """Data of a note; used for create and for full update (PUT)."""

    gift_id: uuid.UUID = Field(
        description="ID of the account's gift idea the note belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    label: Label = Field(description="Label, 1 to 100 characters.", examples=["Größe"])
    text: NoteText = Field(description="Text, 1 to 2000 characters.", examples=["M, eher weit"])


class NoteOut(BaseModel):
    """A note as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Note ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a74"]
    )
    gift_id: uuid.UUID = Field(
        description="ID of the gift idea the note belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    label: str = Field(description="Label.", examples=["Größe"])
    text: str = Field(description="Text.", examples=["M, eher weit"])
