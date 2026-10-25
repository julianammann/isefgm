"""Links and images on a gift idea (F-07)."""

import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base


class AttachmentKind(enum.StrEnum):
    """What an attachment holds: a web link or an uploaded image."""

    LINK = "link"
    IMAGE = "image"


def _kind_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum values, not member names."""
    return [str(member.value) for member in enum_cls]


class Attachment(Base):
    """Labelled link or image on a gift idea (F-07).

    The API exposes links as /links and images as /images; both are rows of this table told
    apart by `kind`. There is no owner_id: an attachment belongs to the account of its gift
    idea, so every query scopes through gift.owner_id (services/link.py, services/image.py).
    The image file itself lies on the uploads volume (core/uploads.py).
    """

    __tablename__ = "attachment"
    __table_args__ = (
        CheckConstraint("kind <> 'link' OR url IS NOT NULL", name="link_has_url"),
        CheckConstraint(
            "kind <> 'image' OR (storage_path IS NOT NULL AND mime_type IS NOT NULL "
            "AND size_bytes IS NOT NULL)",
            name="image_has_file",
        ),
        {
            "comment": "Labelled link or image on a gift idea (F-07), told apart by kind. "
            "Visible only to the owner of the idea (Q-01); deleted together with the idea "
            "and the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key, UUIDv7. Also the list order: oldest attachment first.",
    )
    gift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gift.id", ondelete="CASCADE"),
        index=True,
        comment="Gift idea the attachment belongs to. Deleting the idea deletes it.",
    )
    kind: Mapped[AttachmentKind] = mapped_column(
        Enum(
            AttachmentKind,
            name="attachment_kind",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_kind_values,
        ),
        comment="`link` or `image`.",
    )
    label: Mapped[str] = mapped_column(String(100), comment="Label, e.g. Thalia or Bild vom Laden.")
    url: Mapped[str | None] = mapped_column(
        String(2048), comment="Absolute http or https URL. Required for links, NULL for images."
    )
    storage_path: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        comment="Path of the WebP file relative to UPLOADS_DIR, `<owner_id>/<random>.webp`. "
        "Required for images, NULL for links.",
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        comment="Media type of the stored file, always image/webp. Required for images, "
        "NULL for links.",
    )
    size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        comment="Size of the stored file in bytes. Required for images, NULL for links.",
    )
