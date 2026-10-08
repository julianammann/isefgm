"""Request and response bodies of the link endpoints (F-07)."""

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from giftmanager.schemas.common import Label

# Matches the String(2048) column.
Url = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]


class LinkIn(BaseModel):
    """Data of a link; used for create and for full update (PUT)."""

    gift_id: uuid.UUID = Field(
        description="ID of the account's gift idea the link belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    label: Label = Field(description="Label, 1 to 100 characters.", examples=["Thalia"])
    url: Url = Field(
        description="Absolute http or https URL, up to 2048 characters.",
        examples=["https://www.thalia.de/shop/home/artikeldetails/A1234"],
    )

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> str:
        """Accept only absolute http and https URLs with a host."""
        # TODO(F-07): Raise ValueError for anything else -> 422 with loc ["body", "url"]
        #   (test_invalid_url_is_rejected). The frontend renders the URL as <a href>, so
        #   javascript:, data: and the like must never get through.
        #   Option: pydantic.TypeAdapter(HttpUrl).validate_python(value) inside try/except
        #   ValidationError. Keep returning `value`, not str(...) of the parsed URL: HttpUrl
        #   normalizes, e.g. "https://example.org" becomes "https://example.org/", and the
        #   user should get back what they entered (test_create_and_show_link).
        return value


class LinkOut(BaseModel):
    """A link as the frontend sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Link ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a75"]
    )
    gift_id: uuid.UUID = Field(
        description="ID of the gift idea the link belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    label: str = Field(description="Label.", examples=["Thalia"])
    url: str = Field(
        description="Absolute http or https URL.",
        examples=["https://www.thalia.de/shop/home/artikeldetails/A1234"],
    )
