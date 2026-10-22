"""Request and response bodies of the image endpoints (F-07)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from giftmanager.schemas.common import Label, PageParams


class ImageListParams(PageParams):
    """Pagination for the image list, optionally narrowed to one gift idea."""

    gift_id: uuid.UUID | None = Field(
        default=None, description="Only the images of this gift idea."
    )


class ImageLabelIn(BaseModel):
    """The one editable field of an image; the file itself cannot be replaced."""

    label: Label = Field(description="Label, 1 to 100 characters.", examples=["Bild vom Laden"])


class ImageOut(BaseModel):
    """An image as the frontend sees it; the file comes from `/images/{id}/content`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        description="Image ID (UUIDv7).", examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a76"]
    )
    gift_id: uuid.UUID = Field(
        description="ID of the gift idea the image belongs to.",
        examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
    )
    label: str = Field(description="Label.", examples=["Bild vom Laden"])
    mime_type: str = Field(
        description="Media type of the stored file, always image/webp.", examples=["image/webp"]
    )
    size_bytes: int = Field(description="Size of the stored file in bytes.", examples=[184320])
