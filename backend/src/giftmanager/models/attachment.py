"""Links and images on a gift idea (F-07). Links come first (#28), images follow (#29)."""

import enum
import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base


class AttachmentKind(enum.StrEnum):
    """What an attachment holds: a web link or an uploaded image."""

    LINK = "link"
    IMAGE = "image"


class Attachment(Base):
    """Labelled link or image on a gift idea (F-07).

    The API exposes links as /links and, later, images as /images; both are rows of this
    table told apart by `kind`. There is no owner_id: an attachment belongs to the account of
    its gift idea, so every query scopes through gift.owner_id (services/link.py).
    """

    __tablename__ = "attachment"
    # TODO(F-07): __table_args__ = (
    #       CheckConstraint("kind <> 'link' OR url IS NOT NULL", name="link_has_url"),
    #       -> ck_attachment_link_has_url (test_database_requires_a_url_for_a_link)
    #       {"comment": "..."},
    #   )
    #   #29 adds a matching constraint for images (storage_path, mime_type, size_bytes).

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key, UUIDv7. Also the list order: oldest attachment first.",
    )

    # TODO(F-07): Columns, each with comment=:
    #   gift_id: Mapped[uuid.UUID]
    #       ForeignKey("gift.id", ondelete="CASCADE"), index=True. Deleted with the idea and
    #       with the account (test_deleting_the_idea_deletes_its_links).
    #   kind: Mapped[AttachmentKind]
    #       Enum(AttachmentKind, name="attachment_kind", native_enum=False, length=16,
    #       create_constraint=True, values_callable=...) like Gift.category, so the
    #       database stores `link`, not `LINK`. No default: the service always sets it.
    #   label: Mapped[str]
    #       String(100). Required, e.g. "Thalia" or "Bild vom Laden".
    #   url: Mapped[str | None]
    #       String(2048). Set for links (constraint above), NULL for images.
    #   storage_path, mime_type, size_bytes: not yet, they come with the image upload (#29).
