"""Request and response bodies of the share link endpoints and the shared view (F-14)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from giftmanager.models import GiftCategory
from giftmanager.schemas.person import LinkedPerson


class ShareLinkIn(BaseModel):
    """Data of a share link; used for create and for full update (PUT)."""

    person_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=100,
        description="IDs of the account's people whose gift ideas the link shows, 1 to 100. "
        "Replaces the current selection.",
        examples=[["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71"]],
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        description="Expiry time with time zone, optional. Must lie in the future when it is "
        "set or changed. Null means the link does not expire.",
        examples=["2026-12-24T23:59:59+01:00"],
    )
    active: bool = Field(
        default=True,
        description="False deactivates the link at once; true opens it again.",
        examples=[True],
    )


class ShareLinkOut(BaseModel):
    """A share link as its owner sees it, without the token."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Share link ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a80"]
    )
    people: list[LinkedPerson] = Field(
        description="People whose gift ideas the link shows, sorted by name.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71", "name": "Lena"}]],
    )
    active: bool = Field(description="False once the link is deactivated.", examples=[True])
    expires_at: datetime | None = Field(
        description="Expiry time (UTC), or null if the link does not expire.",
        examples=["2026-12-24T22:59:59Z"],
    )
    created_at: datetime = Field(
        description="Creation time (UTC), set by the server.", examples=["2026-10-15T09:30:00Z"]
    )


class ShareLinkCreated(ShareLinkOut):
    """A new share link together with its token, which is returned only this once."""

    token: str = Field(
        description="Secret token of the link (256 bits, URL-safe). Only its hash is stored, so "
        "it cannot be shown again; the frontend builds the shared URL from it.",
        examples=["q3Xb2k9VtL0mR8sY1nWc4eJ7uA5hZ6oP-dFgQiKjTx0"],
    )


class SharedLinkOut(BaseModel):
    """A web link on a shared gift idea."""

    model_config = ConfigDict(from_attributes=True)

    label: str = Field(description="Label.", examples=["Thalia"])
    url: str = Field(
        description="Absolute http or https URL.",
        examples=["https://www.thalia.de/shop/home/artikeldetails/A1234"],
    )


class SharedImageOut(BaseModel):
    """An image on a shared gift idea; the file comes from `/shared/{token}/images/{id}`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Image ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a76"]
    )
    label: str = Field(description="Label.", examples=["Bild vom Laden"])


class SharedGiftOut(BaseModel):
    """A gift idea in the shared view, without notes, giftings or occasions."""

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
    links: list[SharedLinkOut] = Field(
        description="Web links on the idea, oldest first.",
        examples=[[{"label": "Thalia", "url": "https://www.thalia.de/"}]],
    )
    images: list[SharedImageOut] = Field(
        description="Images on the idea, oldest first.",
        examples=[[{"id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a76", "label": "Bild vom Laden"}]],
    )


class SharedPersonOut(BaseModel):
    """A shared person: only the name, no birthday, relationship or notes."""

    name: str = Field(description="Name.", examples=["Lena"])
    gifts: list[SharedGiftOut] = Field(
        description="Gift ideas meant for the person, newest first.",
        examples=[[]],
    )


class SharedListOut(BaseModel):
    """What a valid share link shows: the chosen people and their gift ideas."""

    owner_name: str = Field(
        description="Display name of the account that shared the list.", examples=["Anna"]
    )
    expires_at: datetime | None = Field(
        description="Expiry time (UTC) of the link, or null.", examples=["2026-12-24T22:59:59Z"]
    )
    people: list[SharedPersonOut] = Field(
        description="Shared people, sorted by name.",
        examples=[[{"name": "Lena", "gifts": []}]],
    )
